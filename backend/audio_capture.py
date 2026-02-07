"""System audio capture via WASAPI loopback for visualization."""

import logging
import threading
import numpy as np

logger = logging.getLogger("radio.audio")


class AudioCapture:
    """Captures system audio via WASAPI loopback, computes FFT at ~30Hz."""

    def __init__(self, num_bands: int = 16, target_fps: int = 30):
        self.num_bands = num_bands
        self.target_fps = target_fps
        self.amplitude: float = 0.0
        self.bands: list[float] = [0.0] * num_bands
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Audio capture started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Audio capture stopped")

    def get_data(self) -> dict:
        """Returns current amplitude + frequency bands (thread-safe)."""
        with self._lock:
            return {
                "amplitude": self.amplitude,
                "bands": list(self.bands),
            }

    def _capture_loop(self):
        import pyaudiowpatch as pyaudio

        p = pyaudio.PyAudio()

        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            logger.error("WASAPI not available on this system")
            p.terminate()
            return

        # Find loopback device matching default output
        loopback = None
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev["hostApi"] == wasapi_info["index"] and dev["maxInputChannels"] > 0:
                name = dev["name"]
                if "[Loopback]" in name or dev.get("isLoopbackDevice", False):
                    loopback = dev
                    break

        if not loopback:
            logger.warning("No WASAPI loopback device found - visualization disabled")
            p.terminate()
            return

        sample_rate = int(loopback["defaultSampleRate"])
        channels = max(1, int(loopback["maxInputChannels"]))
        chunk_size = sample_rate // self.target_fps

        logger.info(f"Loopback device: {loopback['name']} ({sample_rate}Hz, {channels}ch)")

        stream = p.open(
            format=pyaudio.paFloat32,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=loopback["index"],
            frames_per_buffer=chunk_size,
        )

        while self._running:
            try:
                raw = stream.read(chunk_size, exception_on_overflow=False)
                data = np.frombuffer(raw, dtype=np.float32)

                # Mix to mono if stereo
                if channels > 1:
                    data = data.reshape(-1, channels).mean(axis=1)

                # RMS amplitude
                rms = float(np.sqrt(np.mean(data ** 2)))
                amplitude = min(1.0, rms * 4.0)

                # FFT -> frequency bands
                fft = np.abs(np.fft.rfft(data))
                freqs_per_band = max(1, len(fft) // self.num_bands)
                bands = []
                for i in range(self.num_bands):
                    start = i * freqs_per_band
                    end = min(start + freqs_per_band, len(fft))
                    if start < len(fft):
                        band_val = float(np.mean(fft[start:end]))
                        bands.append(min(1.0, band_val * 0.1))
                    else:
                        bands.append(0.0)

                with self._lock:
                    self.amplitude = amplitude
                    self.bands = bands

            except Exception as e:
                logger.error(f"Audio capture error: {e}")

        stream.stop_stream()
        stream.close()
        p.terminate()
