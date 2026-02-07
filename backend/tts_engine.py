"""TTS Engine: F5-TTS wrapper for DJ voice synthesis using Samantha's voice."""

import logging
import re
import time
import numpy as np
import sounddevice as sd
import torch
from pathlib import Path
from threading import Lock

logger = logging.getLogger("radio.tts")


class TTSEngine:
    """F5-TTS for DJ voice synthesis with Samantha's voice.

    Synthesizes text and plays through system speakers (captured by WASAPI loopback).
    """

    def __init__(
        self,
        device: str = "cuda",
        reference_audio: str = "C:/Users/bates/Documents/Coding/samantha/voices/samantha_short.wav",
        reference_text: str | None = None,
        nfe_step: int = 16,
        speed: float = 0.72,
    ):
        self.device = "cuda:0" if device == "cuda" else device
        self.reference_audio = reference_audio
        self.reference_text = reference_text
        self.nfe_step = nfe_step
        self.speed = speed
        self.model = None
        self.sample_rate = 24000
        self._synthesis_lock = Lock()
        self._loaded = False

        # Load reference text from companion .txt file
        if self.reference_text is None:
            txt_path = Path(self.reference_audio).with_suffix(".txt")
            if txt_path.exists():
                self.reference_text = txt_path.read_text(encoding="utf-8").strip()
                logger.info(f"Loaded reference text: '{self.reference_text[:60]}...'")
            else:
                self.reference_text = ""
                logger.warning("No reference text file found - TTS quality may suffer")

    def load(self):
        """Load the F5-TTS model."""
        if self._loaded:
            return

        logger.info(f"Loading F5-TTS model on {self.device}...")

        try:
            from f5_tts.api import F5TTS

            self.model = F5TTS(device=self.device)
            self._loaded = True
            logger.info("F5-TTS loaded successfully")
        except ImportError as e:
            logger.error("F5-TTS not installed. Run: pip install f5-tts")
            raise

    def warmup(self):
        """Run a warmup inference to prime the GPU."""
        if not self._loaded:
            return
        logger.info("Running TTS warmup...")
        try:
            self._synthesize("Hello, this is a warmup.")
            logger.info("TTS warmup complete")
        except Exception as e:
            logger.warning(f"TTS warmup failed: {e}")

    async def synthesize_and_play(self, text: str) -> float:
        """Synthesize text and play through speakers. Returns duration in seconds."""
        if not text.strip():
            return 0.0

        if not self._loaded:
            logger.warning("TTS not loaded, skipping synthesis")
            return 0.0

        logger.info(f"Synthesizing: '{text[:60]}...'")
        start = time.time()

        with self._synthesis_lock:
            audio, sr = self._synthesize(text)

        if audio is None:
            return 0.0

        duration = len(audio) / sr
        logger.info(f"Synthesized {duration:.1f}s audio in {time.time() - start:.1f}s")

        # Play through system speakers (WASAPI loopback captures this)
        sd.play(audio, sr)
        sd.wait()

        return duration

    def _preprocess_text(self, text: str) -> str:
        """Clean text for TTS - normalize punctuation that causes artifacts."""
        # Replace ! with . to prevent high-pitched spikes
        text = text.replace("!", ".")
        # Ellipsis -> comma for natural pause
        text = re.sub(r"\.{2,}", ",", text)
        text = text.replace("\u2026", ",")
        # Em-dash -> comma
        text = text.replace("\u2014", ", ")
        text = text.replace("--", ", ")
        # Remove stage directions *like this*
        text = re.sub(r"\*[^*]+\*", "", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        # Clean comma-comma / comma-period
        text = re.sub(r",\s*,", ",", text)
        text = re.sub(r",\s*\.", ".", text)
        return text.strip()

    def _synthesize(self, text: str) -> tuple[np.ndarray | None, int]:
        """Synthesize audio from text using F5-TTS."""
        text = self._preprocess_text(text)
        if not text:
            return None, 0

        try:
            wav, sr, _ = self.model.infer(
                ref_file=self.reference_audio,
                ref_text=self.reference_text,
                gen_text=text,
                nfe_step=self.nfe_step,
                cfg_strength=2.0,
                sway_sampling_coef=-1.0,
                speed=self.speed,
                cross_fade_duration=0.15,
            )

            # Normalize audio to target loudness
            rms = np.sqrt(np.mean(wav ** 2))
            if rms > 1e-8:
                target_rms = 10 ** (-20.0 / 20.0)  # -20dB
                gain = target_rms / rms
                wav = wav * gain
                # Soft clip
                max_val = np.max(np.abs(wav))
                if max_val > 0.95:
                    wav = np.tanh(wav * 0.95 / max_val) * 0.95

            wav = wav.astype(np.float32)
            return wav, self.sample_rate

        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            return None, 0

    def unload(self):
        """Free GPU memory."""
        if self.model:
            del self.model
            self.model = None
            self._loaded = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("F5-TTS model unloaded")
