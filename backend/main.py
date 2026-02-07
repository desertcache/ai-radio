"""AI Radio Station - FastAPI Backend."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse

from config import RadioConfig
from spotify_controller import SpotifyController
from audio_capture import AudioCapture
from dj import DJBrain
from tts_engine import TTSEngine
from scheduler import RadioScheduler
from demo import DemoScheduler

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("radio.main")

# Global state
config = RadioConfig()
spotify: SpotifyController | None = None
audio_capture: AudioCapture | None = None
dj_brain: DJBrain | None = None
tts_engine: TTSEngine | None = None
scheduler: RadioScheduler | None = None
demo_scheduler: DemoScheduler | None = None
scheduler_task: asyncio.Task | None = None

# WebSocket clients
ws_clients: Set[WebSocket] = set()


async def ws_broadcast(data: dict):
    """Broadcast data to all connected WebSocket clients."""
    if not ws_clients:
        return
    message = json.dumps(data)
    disconnected = set()
    for ws in list(ws_clients):
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    ws_clients -= disconnected


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize and cleanup."""
    global spotify, audio_capture, dj_brain, tts_engine, scheduler

    logger.info(f"Starting AI Radio Station: {config.station_name}")

    # Initialize Spotify controller
    spotify = SpotifyController(
        config.spotify_client_id,
        config.spotify_client_secret,
        config.spotify_redirect_uri,
    )

    # Initialize audio capture
    audio_capture = AudioCapture(
        num_bands=config.audio_fft_bands,
        target_fps=config.audio_target_fps,
    )

    # Initialize DJ brain
    dj_brain = DJBrain(
        station_name=config.station_name,
        dj_name=config.dj_name,
        model=config.ollama_model,
    )

    # Initialize TTS engine (F5-TTS with Samantha's voice)
    tts_engine = TTSEngine(
        device=config.tts_device,
        reference_audio=config.tts_reference_audio,
        nfe_step=config.tts_nfe_step,
        speed=config.tts_speed,
    )

    # Initialize scheduler
    scheduler = RadioScheduler(
        spotify=spotify,
        dj_brain=dj_brain,
        tts_engine=tts_engine,
        audio_capture=audio_capture,
        break_interval=config.break_interval,
        crossfade_duration=config.crossfade_duration,
    )

    logger.info("All components initialized")

    yield

    # Cleanup
    logger.info("Shutting down...")
    if scheduler_task and not scheduler_task.done():
        scheduler_task.cancel()
    if audio_capture:
        audio_capture.stop()
    if tts_engine:
        tts_engine.unload()


app = FastAPI(title="AI Radio Station", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REST API ---

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "station": config.station_name,
        "spotify_auth": spotify.is_authenticated() if spotify else False,
    }


@app.get("/api/spotify/auth")
async def spotify_auth():
    """Redirect to Spotify OAuth."""
    if not spotify:
        return JSONResponse({"error": "Spotify not initialized"}, status_code=500)
    url = spotify.get_auth_url()
    return RedirectResponse(url)


@app.get("/api/spotify/callback")
async def spotify_callback(code: str = Query(...)):
    """Handle Spotify OAuth callback."""
    if not spotify:
        return JSONResponse({"error": "Spotify not initialized"}, status_code=500)
    success = spotify.handle_callback(code)
    if success:
        # Redirect back to frontend
        return RedirectResponse("http://localhost:5173?auth=success")
    return JSONResponse({"error": "Authentication failed"}, status_code=400)


@app.get("/api/spotify/status")
async def spotify_status():
    """Check Spotify auth status and device."""
    if not spotify:
        return {"authenticated": False, "device": None}

    authenticated = spotify.is_authenticated()
    device = None
    if authenticated:
        try:
            device = spotify.find_device()
        except Exception:
            pass

    return {"authenticated": authenticated, "device": device}


@app.get("/api/spotify/playlists")
async def get_playlists():
    """Get user's Spotify playlists."""
    if not spotify or not spotify.is_authenticated():
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    return spotify.get_user_playlists()


@app.post("/api/radio/start")
async def start_radio(body: dict):
    """Start the radio with a playlist."""
    global scheduler_task

    if not spotify or not spotify.is_authenticated():
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    playlist_id = body.get("playlist_id")
    if not playlist_id:
        return JSONResponse({"error": "playlist_id required"}, status_code=400)

    try:
        # Find device
        spotify.find_device()

        # Load TTS if not loaded
        if tts_engine and not tts_engine._loaded:
            tts_engine.load()
            tts_engine.warmup()

        # Start playlist on Spotify
        playlist_uri = f"spotify:playlist:{playlist_id}"
        spotify.play_playlist(playlist_uri, shuffle=True)
        await asyncio.sleep(1)

        # Start scheduler
        if scheduler_task and not scheduler_task.done():
            scheduler_task.cancel()
            await asyncio.sleep(0.5)

        scheduler_task = asyncio.create_task(scheduler.start(ws_broadcast))

        return {"status": "started", "playlist_id": playlist_id}

    except Exception as e:
        logger.error(f"Failed to start radio: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/radio/demo")
async def start_demo():
    """Start demo mode - simulates everything without Spotify."""
    global scheduler_task, demo_scheduler

    # Stop any running scheduler
    if scheduler_task and not scheduler_task.done():
        scheduler_task.cancel()
        await asyncio.sleep(0.5)

    demo_scheduler = DemoScheduler()
    scheduler_task = asyncio.create_task(demo_scheduler.start(ws_broadcast))
    logger.info("Demo mode started")

    return {"status": "demo_started"}


@app.post("/api/radio/stop")
async def stop_radio():
    """Stop the radio."""
    global scheduler_task

    if demo_scheduler:
        await demo_scheduler.stop()
    if scheduler:
        await scheduler.stop()
    if scheduler_task and not scheduler_task.done():
        scheduler_task.cancel()
    if spotify:
        try:
            spotify.pause()
        except Exception:
            pass

    return {"status": "stopped"}


@app.post("/api/radio/skip")
async def skip_track():
    """Skip current track."""
    if scheduler and scheduler._running:
        await scheduler.skip()
        return {"status": "skipped"}
    elif spotify:
        spotify.skip()
        return {"status": "skipped"}
    return JSONResponse({"error": "Radio not running"}, status_code=400)


@app.post("/api/radio/volume")
async def set_volume(body: dict):
    """Set Spotify volume."""
    volume = body.get("volume", 50)
    if spotify:
        spotify.set_volume(int(volume))
        return {"status": "ok", "volume": volume}
    return JSONResponse({"error": "Spotify not available"}, status_code=400)


# --- WebSocket ---

@app.websocket("/ws/radio")
async def websocket_endpoint(ws: WebSocket):
    """Real-time data stream for the radio UI."""
    await ws.accept()
    ws_clients.add(ws)
    logger.info(f"WebSocket client connected (total: {len(ws_clients)})")

    try:
        # Send initial state
        await ws.send_text(json.dumps({
            "type": "station_state",
            "state": scheduler.state if scheduler else "idle",
        }))

        # Send current track if playing
        if spotify and spotify.is_authenticated():
            track = spotify.get_now_playing()
            if track:
                await ws.send_text(json.dumps({
                    "type": "now_playing",
                    "track": track,
                }))

        # Listen for client commands
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            if msg["type"] == "skip":
                await skip_track()
            elif msg["type"] == "set_volume":
                if spotify:
                    spotify.set_volume(int(msg.get("value", 50)))
            elif msg["type"] == "select_playlist":
                playlist_id = msg.get("playlist_id")
                if playlist_id:
                    await start_radio({"playlist_id": playlist_id})
            elif msg["type"] == "request_segment":
                if scheduler and dj_brain and tts_engine:
                    segment = msg.get("segment", "banter")
                    script = await dj_brain.generate_break_segment(scheduler.current_track)
                    await ws_broadcast({"type": "dj_text", "text": script, "segment": segment})
                    await tts_engine.synthesize_and_play(script)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ws_clients.discard(ws)
        logger.info(f"WebSocket client disconnected (total: {len(ws_clients)})")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=False,
        log_level="info",
    )
