"""
ProstudioX — TTS provider (edge-tts, free) with word-level timestamps.

Produces:
  - an MP3 of the spoken script
  - per-word start/end timings (from edge-tts WordBoundary events)
  - an .ass subtitle file with a "word lights up as it's spoken" effect

Run this on Linux/Colab. Requires: pip install edge-tts
"""

import asyncio
import inspect
import os
from dataclasses import dataclass, field

try:
    import edge_tts
except ImportError:  # pragma: no cover
    edge_tts = None


@dataclass
class Word:
    text: str
    start: float  # seconds
    end: float    # seconds


@dataclass
class TTSResult:
    audio_path: str
    subtitle_path: str
    words: list = field(default_factory=list)
    duration: float = 0.0


class TTSProvider:
    """Free neural TTS via Microsoft Edge voices, with word-level timing."""

    DEFAULT_VOICE = "en-US-AriaNeural"  # warm female
    MALE_VOICE = "en-US-GuyNeural"      # clear male

    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = "+0%",
                 volume: str = "+0%"):
        self.voice = voice
        self.rate = rate
        self.volume = volume

    def synthesize(self, text: str, out_dir: str, base_name: str = "voice",
                   highlight_color: str = "&H0000FFFF",   # yellow (ASS BGR)
                   base_color: str = "&H00FFFFFF") -> TTSResult:
        """Render text to audio + word timestamps + word-highlight .ass.

        ASS colors are &HAABBGGRR (alpha, blue, green, red).
        """
        if edge_tts is None:
            raise RuntimeError("edge-tts not installed. Run: pip install edge-tts")

        os.makedirs(out_dir, exist_ok=True)
        audio_path = os.path.join(out_dir, f"{base_name}.mp3")
        subtitle_path = os.path.join(out_dir, f"{base_name}.ass")

        words = asyncio.run(self._synthesize(text, audio_path))
        if not words:
            raise RuntimeError("TTS produced no audio/word boundaries")

        self._write_ass(words, subtitle_path, highlight_color, base_color)

        return TTSResult(
            audio_path=audio_path,
            subtitle_path=subtitle_path,
            words=words,
            duration=words[-1].end,
        )

    async def _synthesize(self, text: str, audio_path: str):
        kwargs = {"rate": self.rate, "volume": self.volume}
        # edge-tts >= 6.1.7 defaults to SentenceBoundary; request word-level
        # boundaries explicitly so we get per-word timestamps for highlighting.
        try:
            if "boundary" in inspect.signature(edge_tts.Communicate).parameters:
                kwargs["boundary"] = "WordBoundary"
        except (TypeError, ValueError):  # pragma: no cover
            pass
        communicate = edge_tts.Communicate(text, self.voice, **kwargs)
        words = []
        with open(audio_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    # edge-tts offsets are in 100-nanosecond ticks
                    start = chunk["offset"] / 1e7
                    dur = chunk["duration"] / 1e7
                    w = chunk["text"].strip()
                    if w:
                        words.append(Word(text=w, start=start, end=start + dur))
        return words

    # ------------------------------------------------------------------ #
    #  Subtitle (.ass) generation with word-level highlight               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _group_lines(words, max_words_per_line=5):
        """Wrap a flat word stream into caption lines (rough, by word count)."""
        lines, current = [], []
        for w in words:
            current.append(w)
            if len(current) >= max_words_per_line:
                lines.append(current)
                current = []
        if current:
            lines.append(current)
        return lines

    @staticmethod
    def _ts(seconds: float) -> str:
        """ASS timestamp: H:MM:SS.cc"""
        cs = int(round(seconds * 100))
        h, rem = divmod(cs, 360000)
        m, rem = divmod(rem, 6000)
        s, c = divmod(rem, 100)
        return f"{h}:{m:02d}:{s:02d}.{c:02d}"

    @staticmethod
    def _esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")

    def _write_ass(self, words, path, highlight_color, base_color):
        lines = self._group_lines(words)
        header = (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "PlayResX: 1080\n"
            "PlayResY: 1920\n"
            "WrapStyle: 2\n"
            "ScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Base,Arial,64,{base_color},{base_color},&H00000000,"
            "&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,40,40,200,1\n"
            f"Style: Highlight,Arial,64,{highlight_color},{highlight_color},"
            "&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,40,40,200,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
            "MarginV, Effect, Text\n"
        )
        out = [header]
        for line in lines:
            if not line:
                continue
            start = self._ts(line[0].start)
            end = self._ts(line[-1].end)
            base_text = " ".join(w.text for w in line)
            out.append(
                f"Dialogue: 0,{start},{end},Base,,0,0,0,,{self._esc(base_text)}"
            )
            for w in line:
                out.append(
                    f"Dialogue: 1,{self._ts(w.start)},{self._ts(w.end)},"
                    f"Highlight,,0,0,0,,{self._esc(w.text)}"
                )
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(out))
