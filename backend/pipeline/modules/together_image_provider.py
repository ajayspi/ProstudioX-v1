"""
ProstudioX — Together AI image provider (free FLUX endpoint).

Runs FLUX.1-schnell (free) via the Together AI images API. Free tier with a
(free) Together API key.

    POST https://api.together.xyz/v1/images/generations
    Authorization: Bearer <TOGETHER_API_KEY>

Set env var: TOGETHER_API_KEY.
"""

import base64
import io
import os
from typing import List, Optional, Tuple

import requests
from PIL import Image


class TogetherImageProvider:
    """FLUX.1-schnell image generation via the Together AI API."""

    name = "together"

    def __init__(self, api_key: str = None,
                 model: str = "black-forest-labs/FLUX.1-schnell-Free",
                 width: int = 768, height: int = 1344, steps: int = 4,
                 timeout: int = 120):
        self.api_key = api_key or os.getenv("TOGETHER_API_KEY")
        self.model = model
        self.width = width
        self.height = height
        self.steps = steps
        self.timeout = timeout

    def generate(self, prompt: str, width: int = None, height: int = None) -> Optional[Image.Image]:
        if not self.api_key:
            return None
        url = "https://api.together.xyz/v1/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "prompt": prompt,
            "width": width or self.width,
            "height": height or self.height,
            "steps": self.steps,
            "n": 1,
            "response_format": "b64_json",
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                b64 = data["data"][0].get("b64_json")
                if b64:
                    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        except Exception:  # pragma: no cover
            return None
        return None

    def generate_batch_images(self, prompts: List[str], style: str = "cinematic",
                              content_theme: bool = False) -> List[Tuple[str, Optional[Image.Image]]]:
        results = []
        for p in prompts:
            styled = f"{p}, {style} style" if style else p
            results.append((p, self.generate(styled)))
        return results
