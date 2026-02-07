"""Radio Scheduler: orchestrates Spotify playback and DJ segments."""

import asyncio
import logging
from typing import Callable, Awaitable

from spotify_controller import SpotifyController
from dj import DJBrain
from tts_engine import TTSEngine
from audio_capture import AudioCapture

logger = logging.getLogger("radio.scheduler")


class RadioScheduler:
    """Orchestrates: Spotify playback -> DJ segments -> repeat."""

    def __init__(
        self,
        spotify: SpotifyController,
        dj_brain: DJBrain,
        tts_engine: TTSEngine,
        audio_capture: AudioCapture,
        break_interval: int = 3,
        crossfade_duration: float = 1.5,
    ):
        self.spotify = spotify
        self.dj = dj_brain
        self.tts = tts_engine
        self.capture = audio_capture
        self.break_interval = break_interval
        self.crossfade_duration = crossfade_duration

        self.songs_since_break = 0
        self.current_track: dict | None = None
        self.state = "idle"  # idle | music | dj_transition | dj_break
        self._running = False
        self._broadcast: Callable | None = None
        self._pregenerated_script: str | None = None
        self._audio_task: asyncio.Task | None = None

    async def start(self, ws_broadcast: Callable[..., Awaitable]):
        """Start the radio loop."""
        self._broadcast = ws_broadcast
        self._running = True
        self.capture.start()

        # Start audio data broadcast
        self._audio_task = asyncio.create_task(self._broadcast_audio_data())

        logger.info("Radio scheduler started")

        try:
            await self._radio_loop()
        except asyncio.CancelledError:
            logger.info("Radio scheduler cancelled")
        except Exception as e:
            logger.error(f"Radio scheduler error: {e}", exc_info=True)
        finally:
            self._running = False
            self.capture.stop()
            if self._audio_task:
                self._audio_task.cancel()

    async def stop(self):
        """Stop the radio."""
        self._running = False
        self.state = "idle"
        self.capture.stop()
        if self._audio_task:
            self._audio_task.cancel()
        await self._send({"type": "station_state", "state": "idle"})
        logger.info("Radio scheduler stopped")

    async def skip(self):
        """Skip current track immediately."""
        self.spotify.skip()
        await asyncio.sleep(0.5)
        self.current_track = self.spotify.get_now_playing()
        if self.current_track:
            await self._send({"type": "now_playing", "track": self.current_track})

    async def _radio_loop(self):
        """Main radio loop."""
        # Get initial track info
        self.current_track = self.spotify.get_now_playing()
        if self.current_track:
            self.state = "music"
            await self._send({"type": "now_playing", "track": self.current_track})
            await self._send({"type": "station_state", "state": "music"})

        while self._running:
            # Wait for track to near end
            self.state = "music"
            await self._send({"type": "station_state", "state": "music"})
            await self._wait_for_track_near_end()

            if not self._running:
                break

            # Fade out Spotify
            self.state = "dj_transition"
            await self._send({"type": "station_state", "state": "dj_transition"})
            await self._fade_spotify_volume(100, 0, self.crossfade_duration)

            # Pause Spotify during DJ segment
            self.spotify.pause()
            await asyncio.sleep(0.3)

            # Generate DJ content (use pregenerated if available)
            if self._pregenerated_script:
                script = self._pregenerated_script
                self._pregenerated_script = None
            elif self.songs_since_break >= self.break_interval:
                script = await self.dj.generate_break_segment(self.current_track)
                self.state = "dj_break"
                await self._send({"type": "station_state", "state": "dj_break"})
                self.songs_since_break = 0
            else:
                script = await self.dj.generate_transition(self.current_track, None)

            # Send DJ text and speak
            await self._send({"type": "dj_text", "text": script, "segment": self.state})
            await self.tts.synthesize_and_play(script)
            await asyncio.sleep(0.3)

            # Skip to next track
            self.spotify.skip()
            await asyncio.sleep(0.5)

            # Fade Spotify back up
            self.spotify.resume()
            await self._fade_spotify_volume(0, 100, self.crossfade_duration)

            # Update current track
            self.current_track = self.spotify.get_now_playing()
            self.songs_since_break += 1
            self.state = "music"

            if self.current_track:
                await self._send({"type": "now_playing", "track": self.current_track})
            await self._send({"type": "station_state", "state": "music"})

            # Pre-generate next DJ segment while music plays
            asyncio.create_task(self._pregenerate_next())

    async def _broadcast_audio_data(self):
        """Send FFT + amplitude data at ~30Hz."""
        poll_count = 0
        while self._running:
            data = self.capture.get_data()

            await self._send({
                "type": "audio_data",
                "amplitude": data["amplitude"],
                "bands": data["bands"],
                "state": self.state,
            })

            # Send track progress every ~2 seconds (every 60 frames at 30fps)
            poll_count += 1
            if poll_count % 60 == 0 and self.state == "music":
                track = self.spotify.get_now_playing()
                if track:
                    self.current_track = track
                    await self._send({
                        "type": "track_progress",
                        "progress_ms": track["progress_ms"],
                        "duration_ms": track["duration_ms"],
                    })

            await asyncio.sleep(1 / 30)

    async def _fade_spotify_volume(self, from_vol: int, to_vol: int, duration: float = 1.5):
        """Smooth volume ramp."""
        steps = 15
        delay = duration / steps
        for i in range(steps + 1):
            if not self._running:
                break
            vol = int(from_vol + (to_vol - from_vol) * (i / steps))
            self.spotify.set_volume(vol)
            await asyncio.sleep(delay)

    async def _wait_for_track_near_end(self):
        """Poll Spotify until current track is within 5 seconds of ending."""
        while self._running:
            info = self.spotify.get_now_playing()
            if info:
                self.current_track = info
                remaining = info["duration_ms"] - info["progress_ms"]
                if remaining < 5000:
                    break
            await asyncio.sleep(2)

    async def _pregenerate_next(self):
        """Pre-generate the next DJ segment while music plays."""
        try:
            if self.songs_since_break >= self.break_interval:
                script = await self.dj.generate_break_segment(self.current_track)
            else:
                script = await self.dj.generate_transition(self.current_track, None)
            self._pregenerated_script = script
            logger.info(f"Pre-generated DJ segment ({len(script)} chars)")
        except Exception as e:
            logger.warning(f"Pre-generation failed: {e}")

    async def _send(self, data: dict):
        """Broadcast data to WebSocket clients."""
        if self._broadcast:
            await self._broadcast(data)
