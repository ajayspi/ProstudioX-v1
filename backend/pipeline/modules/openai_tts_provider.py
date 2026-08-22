"""
ProstudioX — OpenAI TTS provider (uses your existing OPENAI_API_KEY).

Voices: alloy, echo, fable, onyx, nova, shimmer.
Models: tts-1 (fast, cheap) or tts-1-hd (higher quality).
No word-level timestamps -> returns a TTSResult without subtitle/words.
"""

import os

from modules.tts_provider import TTSResult


class OpenAITTSProvider:
    """High-quality TTS via the OpenAI audio API."""

    name = "openai"

    def __init__(self, api_key: str = None, voice: str = "alloy", model: str = "tts-1"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.voice = voice
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def synthesize(self, text: str, out_dir: str, base_name: str = "voice") -> TTSResult:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        os.makedirs(out_dir, exist_ok=True)
        audio_path = os.path.join(out_dir, f"{base_name}.mp3")
        client = self._get_client()
        resp = client.audio.speech.create(
            model=self.model, voice=self.voice, input=text
        )
        if hasattr(resp, "stream_to_file"):
            resp.stream_to_file(audio_path)
        else:  # pragma: no cover - older openai clients
            resp.write_to_file(audio_path)

        est_duration = max(1.0, len(text.split()) / 2.6)
        return TTSResult(
            audio_path=audio_path, subtitle_path="", words=[], duration=est_duration
        )
