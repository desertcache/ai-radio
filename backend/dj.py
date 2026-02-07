"""DJ Brain: generates radio content using Ollama."""

import logging
import random
import ollama

logger = logging.getLogger("radio.dj")

SEGMENT_TYPES = ["transition", "banter", "news", "weather", "ad", "station_id"]


class DJBrain:
    """Generates DJ scripts using Ollama LLM."""

    def __init__(self, station_name: str, dj_name: str, model: str = "qwen3:8b"):
        self.station_name = station_name
        self.dj_name = dj_name
        self.model = model
        self.history: list[dict] = []
        self._system_prompt = self._build_system_prompt()
        logger.info(f"DJBrain initialized: {dj_name} on {station_name} (model: {model})")

    def _build_system_prompt(self) -> str:
        return f"""You are {self.dj_name}, a charismatic late-night radio DJ on {self.station_name}.

Your personality:
- Smooth, warm, and slightly irreverent
- You love music and have deep knowledge of it
- You crack dry jokes and make witty observations
- You have a signature laid-back delivery
- You occasionally reference the time of night and the vibe

Rules for your output:
- Write ONLY the words you would speak out loud. No stage directions, no asterisks, no parentheticals.
- Keep it concise: 2-4 sentences max for transitions, 3-6 sentences for breaks.
- Reference the actual song titles, artists, and musical qualities when given track info.
- Sound natural and conversational, like real radio DJ patter.
- Never use markdown, bullet points, or formatting.
- Never say "Here's" at the start - vary your intros.
- Do NOT include any thinking tags or reasoning. Just the DJ script."""

    async def generate_transition(self, current_track: dict | None, next_track: dict | None) -> str:
        """Generate a short DJ transition between songs."""
        prompt_parts = ["Generate a short DJ transition (2-3 sentences)."]

        if current_track:
            prompt_parts.append(
                f"Just played: \"{current_track['title']}\" by {current_track['artist']}."
            )
        if next_track:
            prompt_parts.append(
                f"Coming up next: \"{next_track['title']}\" by {next_track['artist']}."
            )

        prompt_parts.append("Bridge from the last song to the next with your signature style.")

        return await self._generate("\n".join(prompt_parts))

    async def generate_break_segment(self, current_track: dict | None) -> str:
        """Generate a longer DJ break segment (news/weather/banter/ad)."""
        segment = random.choice(["banter", "news", "weather", "ad", "station_id"])

        prompts = {
            "banter": (
                "Do a short DJ banter segment. Share a quirky observation, "
                "a fun music fact, or a late-night thought. Keep it to 3-4 sentences."
            ),
            "news": (
                "Read a short fictional/satirical news headline and brief commentary. "
                "Make it absurd but delivered deadpan. 2-3 sentences."
            ),
            "weather": (
                "Give a completely fictional and absurd weather report for your listeners. "
                "Make it atmospheric and poetic. 2-3 sentences."
            ),
            "ad": (
                "Do a fake radio ad for a ridiculous fictional product or local business. "
                "Make it funny but delivered straight. 3-4 sentences."
            ),
            "station_id": (
                f"Do a station identification. Remind listeners they're tuned to "
                f"{self.station_name} with {self.dj_name}. Add a little flavor. 1-2 sentences."
            ),
        }

        prompt = prompts[segment]
        if current_track:
            prompt += f"\nContext: You just played \"{current_track['title']}\" by {current_track['artist']}."

        script = await self._generate(prompt)
        return script

    async def generate_intro(self, track: dict) -> str:
        """Generate a song intro."""
        prompt = (
            f"Introduce the next song: \"{track['title']}\" by {track['artist']}. "
            f"1-2 sentences, build anticipation."
        )
        return await self._generate(prompt)

    async def _generate(self, prompt: str) -> str:
        """Generate text using Ollama."""
        try:
            client = ollama.Client()
            response = client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": prompt},
                ],
                options={
                    "num_ctx": 2048,
                    "temperature": 0.9,
                    "top_p": 0.95,
                },
                stream=False,
            )

            text = response["message"]["content"].strip()

            # Clean up any thinking tags that qwen might include
            if "<think>" in text:
                # Remove everything between <think> and </think>
                import re
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

            # Strip any remaining markdown or formatting artifacts
            text = text.strip('"').strip("*").strip()

            logger.info(f"DJ generated ({len(text)} chars): {text[:80]}...")
            return text

        except Exception as e:
            logger.error(f"DJ generation failed: {e}")
            return f"You're listening to {self.station_name}. Stay tuned."
