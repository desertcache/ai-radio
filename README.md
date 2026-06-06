<!-- screenshot/GIF: add a short demo GIF here -->

# AI Radio — KPXL Nocturnal Radio

**A self-hosted AI radio station with a live, talking DJ — local LLM writes the patter, on-device voice synthesis speaks it, and it weaves itself between your Spotify tracks in real time.**

AI Radio runs a fully local virtual DJ ("Nyx") that watches what's playing, generates spoken radio segments with a local Ollama model, voices them with on-device F5-TTS, and ducks the music to talk over the transition, all streamed to a React UI with live audio-reactive visuals. Everything except Spotify itself runs on your own machine: no cloud LLM, no cloud TTS. There is also a YouTube/local-file mode and a Spotify-free demo mode so it still does something without credentials.

## What's hard about this

The interesting problems here are about timing and orchestration across three independent, slow, non-deterministic subsystems (music playback, an LLM, and a neural vocoder) that all share one audio output.

- **Talking *between* songs without dead air or talking over the music.** The scheduler (`backend/scheduler.py`) polls Spotify playback position and only triggers a DJ break once the current track is within 5 seconds of ending (`_wait_for_track_near_end`). It then runs a scripted hand-off: ramp Spotify volume `100 -> 0` over a 15-step crossfade, pause playback, speak the segment, skip to the next track, then ramp `0 -> 100` back up. The break cadence is stateful (`songs_since_break` vs. a configurable `break_interval`), so most transitions are short bridges and every Nth one is a longer banter/news/weather/ad/station-ID segment.
- **Hiding LLM + TTS latency behind the music.** Generating a script with Ollama and synthesizing it with F5-TTS takes seconds, too long to do at the moment of transition. The scheduler pre-generates the *next* DJ segment in a background `asyncio.Task` while the current song plays (`_pregenerate_next`), caches the script, and consumes it instantly when the transition fires. This is the difference between a snappy hand-off and several seconds of silence.
- **An on-device F5-TTS pipeline that actually sounds like radio.** The TTS wrapper (`backend/tts_engine.py`) does zero-shot voice cloning from a reference clip + reference transcript, with a lazy model load and a GPU warmup inference (first inference on CUDA is slow, so it is primed at start). It also does the unglamorous-but-necessary work: text preprocessing that strips stage directions (`*...*`), converts `!` to `.` to kill pitch spikes, and normalizes ellipses/dashes into natural pauses; plus RMS loudness normalization to a -20 dB target with a `tanh` soft-clip so segments do not blow out the mix. Synthesis is guarded by a lock so concurrent requests cannot collide on the model.
- **Getting the LLM to behave like a DJ, not a chatbot.** `backend/dj.py` uses a persona system prompt plus per-segment prompts, and post-processes the output to strip qwen's `<think>...</think>` reasoning blocks and stray markdown/quotes, because raw model output is full of things you cannot say out loud.
- **Real-time audio-reactive UI without melting the browser.** Audio is captured *from system output* via WASAPI loopback (`backend/audio_capture.py`), so the visuals react to the actual mixed sound (music *and* the DJ's voice), not a separate stream. A background thread computes RMS amplitude and an FFT split into 16 frequency bands at ~30 Hz and broadcasts it over WebSocket. On the frontend (`frontend/src/hooks/useRadioSocket.ts`), this high-frequency stream is deliberately written to a `useRef` instead of React state, so the canvas-based VU meters and frequency bars read it at 30 fps **without triggering a React re-render on every frame**; only low-frequency events (now-playing, DJ text, station state) flow through `setState`.
- **Plumbing it all together cleanly.** `backend/main.py` is a FastAPI app using a `lifespan` context manager to initialize/tear down every subsystem, with graceful degradation throughout: missing Spotify creds, a failed F5-TTS load, or no loopback device each disable just that feature instead of crashing the station. A single WebSocket endpoint multiplexes both the outbound data stream and inbound client commands (skip, volume, playlist select).

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python, FastAPI, Uvicorn, `asyncio`, WebSockets |
| AI DJ | Ollama (`qwen3:8b`) for script generation |
| Voice | F5-TTS (zero-shot voice cloning) on CUDA via PyTorch, played out with `sounddevice` |
| Music | Spotify Web API via Spotipy (OAuth, playback control, now-playing); local-file/YouTube mode as alternative |
| Audio analysis | WASAPI loopback capture (`PyAudioWPatch`) + NumPy FFT, 16 bands @ ~30 Hz |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, canvas-based VU meters & frequency bars |

## Run it

**Prerequisites**
- Python 3.11+ and a CUDA-capable GPU (F5-TTS runs on `cuda` by default; without it, the station still runs but with no voice)
- Node.js 18+
- [Ollama](https://ollama.com) running locally with the model pulled: `ollama pull qwen3:8b`
- Windows (audio capture uses WASAPI loopback via `PyAudioWPatch`)
- For Spotify mode: a Spotify Premium account and a registered app for API credentials
- F5-TTS expects a reference voice clip + matching transcript; the reference paths are configurable in `backend/config.py`

**Environment** — create `backend/.env`:
```
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```

**Start everything** (Windows) — launches the FastAPI backend on `:8000`, the Vite dev server on `:5173`, and opens the browser:
```
start.bat
```

**Or run each side manually:**
```bash
# Backend (FastAPI on :8000)
cd backend
pip install -r requirements.txt
python main.py

# Frontend (Vite on :5173)
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173. Authenticate with Spotify and pick a playlist, or hit the YouTube/local-file mode (plays bundled tracks in `backend/tracks/`), or run demo mode to see the DJ + UI without any Spotify setup.

> Most settings — station/DJ name, Ollama model, TTS device/speed/quality (`nfe_step`), DJ break interval, crossfade duration, FFT band count — live in one place: the `RadioConfig` dataclass in `backend/config.py`.
