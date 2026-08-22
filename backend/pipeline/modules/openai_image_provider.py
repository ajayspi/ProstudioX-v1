"""
ProstudioX — OpenAI image provider (uses your existing OPENAI_API_KEY).

Models: gpt-image-1 (default, returns base64) or dall-e-3 (returns URL).
Portrait sizes for Shorts: 1024x1536.
"""

import base64
import io
import os
from typing import List, Optional, Tuple

from PIL import Image


class OpenAIImageProvider:
    """DALL-E / gpt-image generation via the OpenAI API."""

    name = "openai"

    def __init__(self, api_key: str = None, model: str = "gpt-image-1",
                 size: str = "1024x1536"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.size = size
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str, size: str = None) -> Optional[Image.Image]:
        if not self.api_key:
            return None
        try:
            client = self._get_client()
            resp = client.images.generate(
                model=self.model, prompt=prompt, size=size or self.size, n=1
            )
            data = resp.data[0]
            if getattr(data, "b64_json", None):
                return Image.open(io.BytesIO(base64.b64decode(data.b64_json))).convert("RGB")
            url = getattr(data, "url", None)
            if url:
                import requests
                r = requests.get(url, timeout=60)
                if r.status_code == 200:
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
