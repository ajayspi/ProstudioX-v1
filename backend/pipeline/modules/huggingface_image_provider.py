"""
ProstudioX — Hugging Face Inference image provider (free tier).

Runs open-source image models (FLUX.1-schnell / FLUX.1-dev, SDXL, etc.) via the
Hugging Face Inference API. Free tier; requires a (free) HF token.

    POST https://api-inference.huggingface.co/models/<model>
    Authorization: Bearer <HF_TOKEN>

Set env var: HUGGINGFACE_API_KEY (or HF_TOKEN).
"""

import io
import os
from typing import List, Optional, Tuple

import requests
from PIL import Image


class HuggingFaceImageProvider:
    """FLUX / SDXL image generation via the Hugging Face Inference API."""

    name = "huggingface"

    def __init__(self, api_key: str = None, model: str = "black-forest-labs/FLUX.1-schnell",
                 width: int = 768, height: int = 1344, timeout: int = 120):
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
        self.model = model
        self.width = width
        self.height = height
        self.timeout = timeout

    def generate(self, prompt: str, width: int = None, height: int = None) -> Optional[Image.Image]:
        if not self.api_key:
            return None
        url = f"https://api-inference.huggingface.co/models/{self.model}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"inputs": prompt}
        # Best-effort portrait sizing (some backends honor this, others ignore it)
        try:
            payload["parameters"] = {"width": width or self.width,
                                     "height": height or self.height}
        except Exception:  # pragma: no cover
            pass
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                return Image.open(io.BytesIO(r.content)).convert("RGB")
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
