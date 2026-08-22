"""
ProstudioX — Pollinations.ai image provider (FREE, no API key required).

Serves AI-generated images over a plain HTTP GET:
    https://image.pollinations.ai/prompt/<encoded prompt>?width=..&height=..&model=..

Models available (2026): flux, turbo, gptimage, seedream, etc.
"""

import io
import urllib.parse
from typing import List, Optional, Tuple

import requests
from PIL import Image


class PollinationsImageProvider:
    """Free, keyless AI image generation via Pollinations.ai."""

    name = "pollinations"

    def __init__(self, model: str = "flux", width: int = 1080, height: int = 1920,
                 timeout: int = 90):
        self.model = model
        self.width = width
        self.height = height
        self.timeout = timeout

    def generate(self, prompt: str, width: int = None, height: int = None,
                 seed: int = None) -> Optional[Image.Image]:
        w = width or self.width
        h = height or self.height
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
        params = {"width": w, "height": h, "model": self.model, "nologo": "true"}
        if seed is not None:
            params["seed"] = seed
        try:
            r = requests.get(url, params=params, timeout=self.timeout)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                return Image.open(io.BytesIO(r.content)).convert("RGB")
        except Exception:  # pragma: no cover - network flakiness
            return None
        return None

    def generate_batch_images(self, prompts: List[str], style: str = "cinematic",
                              content_theme: bool = False) -> List[Tuple[str, Optional[Image.Image]]]:
        """Same signature as GeminiImageGenerator for drop-in use."""
        results = []
        for p in prompts:
            styled = f"{p}, {style} style" if style else p
            results.append((p, self.generate(styled)))
        return results
