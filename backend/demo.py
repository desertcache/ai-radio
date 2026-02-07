"""Demo mode: simulates the full radio experience without Spotify or TTS."""

import asyncio
import math
import random
import logging
import time

logger = logging.getLogger("radio.demo")

# Fake track library with real Spotify album art URLs (public CDN)
DEMO_TRACKS = [
    {
        "id": "demo1", "uri": "spotify:track:demo1",
        "title": "Midnight City",
        "artist": "M83",
        "album": "Hurry Up, We're Dreaming",
        "art_url": "https://i.scdn.co/image/ab67616d0000b273ef4d5c1b9e7715ee70327df4",
        "duration_ms": 243000,
    },
    {
        "id": "demo2", "uri": "spotify:track:demo2",
        "title": "Breathe",
        "artist": "Telepopmusik",
        "album": "Genetic World",
        "art_url": "https://i.scdn.co/image/ab67616d0000b273c84a1ac4af498a4be6cf498a",
        "duration_ms": 276000,
    },
    {
        "id": "demo3", "uri": "spotify:track:demo3",
        "title": "Teardrop",
        "artist": "Massive Attack",
        "album": "Mezzanine",
        "art_url": "https://i.scdn.co/image/ab67616d0000b27374379e03e3ee18f899e3ae9e",
        "duration_ms": 326000,
    },
    {
        "id": "demo4", "uri": "spotify:track:demo4",
        "title": "To Build a Home",
        "artist": "The Cinematic Orchestra",
        "album": "Ma Fleur",
        "art_url": "https://i.scdn.co/image/ab67616d0000b2730bac5a3a4e77f8b2e36bcf5e",
        "duration_ms": 361000,
    },
    {
        "id": "demo5", "uri": "spotify:track:demo5",
        "title": "Intro",
        "artist": "The xx",
        "album": "xx",
        "art_url": "https://i.scdn.co/image/ab67616d0000b273bfb30c8863ffc8e8e4f4e6f5",
        "duration_ms": 128000,
    },
]

DJ_TRANSITIONS = [
    "That was smooth. Real smooth. The kind of track that makes you forget what time it is, and honestly, that's the whole point of being here tonight.",
    "Mmm. You felt that one, right? I know I did. Let the reverb wash over you for a second before we move on.",
    "We're deep into the night now, just you and me and the music. No place I'd rather be. Coming up, something to keep the mood alive.",
    "That track never gets old. Every time I hear it, I notice something new. A little texture hiding in the background, a note that catches you off guard.",
    "If you're still up, you're my kind of people. Night owls unite. Let's keep this going.",
]

DJ_BREAKS = [
    "You're locked in with KPXL Nocturnal Radio. I'm Nyx, and I'll be right here with you until the sun decides to show up. No rush though.",
    "Breaking news from the KPXL newsroom. Local cat reportedly stared at wall for forty-seven minutes before walking away. Experts say, and I quote, this is extremely normal.",
    "Time for the weather. Tonight we're looking at a thick blanket of stars with a chance of existential wonder. Temperatures are irrelevant because you're indoors listening to great music.",
    "A word from our sponsors. Tired of sleeping? Try Nocturnal Brand Insomnia Coffee. It's three AM somewhere, and that somewhere is right here.",
    "Quick thought for the late night crew. You know what's underrated? Silence. Just a moment of it. Here, let me give you one. Okay that's enough, back to the music.",
]


class DemoScheduler:
    """Simulates the full radio experience with fake data."""

    def __init__(self):
        self.state = "idle"
        self._running = False
        self._broadcast = None
        self._track_index = 0
        self._songs_since_break = 0

    async def start(self, ws_broadcast):
        """Start the demo loop."""
        self._broadcast = ws_broadcast
        self._running = True
        self.state = "music"

        logger.info("Demo mode started")

        # Start audio simulation + radio loop concurrently
        audio_task = asyncio.create_task(self._simulate_audio())
        radio_task = asyncio.create_task(self._radio_loop())

        try:
            await asyncio.gather(audio_task, radio_task)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False

    async def stop(self):
        self._running = False
        self.state = "idle"
        if self._broadcast:
            await self._broadcast({"type": "station_state", "state": "idle"})

    async def _radio_loop(self):
        """Simulate the music -> DJ -> music cycle."""
        while self._running:
            # Pick a track
            track = dict(DEMO_TRACKS[self._track_index % len(DEMO_TRACKS)])
            track["progress_ms"] = 0
            track["is_playing"] = True
            self._track_index += 1

            # Send now playing
            self.state = "music"
            await self._send({"type": "station_state", "state": "music"})
            await self._send({"type": "now_playing", "track": track})

            # Simulate track playing (compressed: 15s per "song" in demo)
            demo_duration_s = 15
            steps = demo_duration_s * 2  # Update every 0.5s
            for i in range(steps):
                if not self._running:
                    return
                progress = int((i / steps) * track["duration_ms"])
                await self._send({
                    "type": "track_progress",
                    "progress_ms": progress,
                    "duration_ms": track["duration_ms"],
                })
                await asyncio.sleep(0.5)

            # DJ transition
            self._songs_since_break += 1

            if self._songs_since_break >= 3:
                # Longer break
                self.state = "dj_break"
                await self._send({"type": "station_state", "state": "dj_break"})
                dj_text = random.choice(DJ_BREAKS)
                await self._send({"type": "dj_text", "text": dj_text, "segment": "dj_break"})
                # Simulate DJ speaking (longer)
                await asyncio.sleep(6)
                self._songs_since_break = 0
            else:
                # Short transition
                self.state = "dj_transition"
                await self._send({"type": "station_state", "state": "dj_transition"})
                dj_text = random.choice(DJ_TRANSITIONS)
                await self._send({"type": "dj_text", "text": dj_text, "segment": "dj_transition"})
                await asyncio.sleep(4)

    async def _simulate_audio(self):
        """Generate fake audio data at 30Hz for VU meters + frequency bars."""
        t = 0.0
        dt = 1.0 / 30.0

        while self._running:
            t += dt

            if self.state in ("dj_transition", "dj_break"):
                # DJ speaking: rhythmic voice-like pattern
                base = 0.3 + 0.2 * math.sin(t * 8.0)
                amplitude = base + random.uniform(-0.05, 0.05)
                # Voice-like frequency distribution (mid-heavy)
                bands = []
                for i in range(16):
                    if 3 <= i <= 8:  # Voice range
                        val = 0.3 + 0.3 * math.sin(t * 6.0 + i * 0.5) + random.uniform(0, 0.1)
                    else:
                        val = random.uniform(0, 0.08)
                    bands.append(max(0.0, min(1.0, val)))
            elif self.state == "music":
                # Music: rich full-spectrum with beat pulse
                beat_phase = (t * 2.0) % 1.0  # ~120 BPM
                beat_kick = max(0, 1.0 - beat_phase * 4.0)  # Sharp kick decay
                base_amplitude = 0.4 + 0.25 * beat_kick + 0.1 * math.sin(t * 3.7)
                amplitude = base_amplitude + random.uniform(-0.03, 0.03)

                bands = []
                for i in range(16):
                    # Bass (0-3): strong with beat
                    if i < 4:
                        val = 0.5 * beat_kick + 0.2 + random.uniform(0, 0.15)
                    # Mids (4-10): melodic movement
                    elif i < 11:
                        val = 0.25 + 0.2 * math.sin(t * 4.0 + i * 0.8) + random.uniform(0, 0.12)
                    # Highs (11-15): shimmer
                    else:
                        val = 0.1 + 0.15 * math.sin(t * 7.0 + i * 1.2) + random.uniform(0, 0.1)
                    bands.append(max(0.0, min(1.0, val)))
            else:
                # Idle
                amplitude = 0.0
                bands = [0.0] * 16

            await self._send({
                "type": "audio_data",
                "amplitude": max(0.0, min(1.0, amplitude)),
                "bands": bands,
                "state": self.state,
            })

            await asyncio.sleep(dt)

    async def _send(self, data: dict):
        if self._broadcast:
            await self._broadcast(data)
