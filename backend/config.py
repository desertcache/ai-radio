"""Configuration for AI Radio Station."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RadioConfig:
    """Central configuration for all radio components."""

    # Station identity
    station_name: str = "KPXL Nocturnal Radio"
    dj_name: str = "Nyx"
    dj_tagline: str = "Your late-night companion on the airwaves"

    # Spotify
    spotify_client_id: str = field(default_factory=lambda: os.getenv("SPOTIFY_CLIENT_ID", ""))
    spotify_client_secret: str = field(default_factory=lambda: os.getenv("SPOTIFY_CLIENT_SECRET", ""))
    spotify_redirect_uri: str = field(default_factory=lambda: os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback"))

    # Ollama (DJ Brain)
    ollama_model: str = "qwen3:8b"
    ollama_num_gpu_layers: int | None = None

    # TTS (F5-TTS with Samantha's voice)
    tts_device: str = "cuda"
    tts_reference_audio: str = "C:/Users/bates/Documents/Coding/samantha/voices/samantha_short.wav"
    tts_nfe_step: int = 16  # Lower = faster, higher = better quality (8-32)
    tts_speed: float = 0.72

    # Audio capture
    audio_fft_bands: int = 16
    audio_target_fps: int = 30

    # Scheduler
    break_interval: int = 3  # DJ break every N songs
    track_end_threshold_ms: int = 5000  # Start transition when track has this many ms left
    crossfade_duration: float = 1.5  # Volume crossfade duration in seconds

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
