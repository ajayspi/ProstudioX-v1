"""
ProstudioX — Google Translate TTS provider (FREE, no API key required).

Lower quality than edge-tts and no word-level timestamps, but works as a
zero-config fallback. Returns a TTSResult with empty words / no subtitle,
so the pipeline renders the voiceover without word highlighting.
"""

import os

from modules.tts_provider import TTSResult


class GoogleTranslateTTSProvider:
    """Free TTS via gTTS (Google Translate voice)."""

    name = "gtts"

    def __init__(self, lang: str = "en", tld: str = "com"):
        self.lang = lang
        self.tld = tld

    def synthesize(self, text: str, out_dir: str, base_name: str = "voice") -> TTSResult:
        try:
            from gtts import gTTS
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("gtts not installed. Run: pip install gTTS") from e

        os.makedirs(out_dir, exist_ok=True)
        audio_path = os.path.join(out_dir, f"{base_name}.mp3")
        tts = gTTS(text=text, lang=self.lang, tld=self.tld)
        tts.save(audio_path)

        # No word boundaries available -> estimate duration from word count.
        words = text.split()
        est_duration = max(1.0, len(words) / 2.6)
        return TTSResult(
            audio_path=audio_path, subtitle_path="", words=[], duration=est_duration
        )
