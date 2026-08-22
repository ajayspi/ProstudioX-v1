"""
ProstudioX — optional image-to-video providers (motion).

Convert a static image into a short video clip using a hosted model API, so a
Short can have real camera motion instead of a Ken Burns zoom. Fully optional:
if no API key is set, or the call fails, the pipeline falls back to static
images (Ken Burns) automatically.

Providers:
  - replicate  (default) — Wan 2.1 image-to-video on Replicate (free signup credits)
  - fal        — Wan/Kling image-to-video on fal.ai (free credits)

Keys (env vars, never committed):
  REPLICATE_API_TOKEN
  FAL_KEY
"""

import base64
import os
import time

import requests


def _image_to_data_uri(image_path: str) -> str:
    """Encode a local image as a base64 data URI for API upload."""
    with open(image_path, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode("ascii")
    ext = os.path.splitext(image_path)[1].lower().lstrip(".") or "png"
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{b64}"


def _download(url: str, out_path: str, timeout: int = 120) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:  # pragma: no cover
        return False
    return False


class ReplicateImageToVideo:
    """Image-to-video via Replicate (Wan 2.1 i2v by default)."""

    name = "replicate"

    def __init__(self, model: str = "wan-video/wan-2.1-i2v",
                 timeout: int = 300):
        self.model = model
        self.timeout = timeout

    def animate(self, image_path: str, out_path: str, prompt: str = "",
                duration: float = 4.0) -> str:
        token = os.getenv("REPLICATE_API_TOKEN")
        if not token:
            return None

        data_uri = _image_to_data_uri(image_path)
        # Replicate accepts a data URI for the image input; extra fields are
        # passed through to the model (prompt / duration). Adjust `self.model`
        # to match a current image-to-video model in the Replicate catalog.
        body = {
            "input": {
                "image": data_uri,
                "prompt": prompt or "subtle camera movement, cinematic",
                "duration": max(1, int(round(duration))),
            }
        }
        headers = {"Authorization": f"Bearer {token}",
                   "Content-Type": "application/json"}

        owner, name = self.model.split("/", 1)
        url = f"https://api.replicate.com/v1/models/{owner}/{name}/predictions"
        try:
            r = requests.post(url, json=body, headers=headers, timeout=60)
            r.raise_for_status()
            prediction = r.json()
        except Exception:  # pragma: no cover
            return None

        # Poll until the prediction finishes.
        p_url = f"https://api.replicate.com/v1/predictions/{prediction.get('id')}"
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                r = requests.get(p_url, headers=headers, timeout=30)
                r.raise_for_status()
                p = r.json()
            except Exception:  # pragma: no cover
                return None
            status = p.get("status")
            if status == "succeeded":
                out = p.get("output")
                video_url = out[0] if isinstance(out, list) and out else out
                if video_url and _download(video_url, out_path):
                    return out_path
                return None
            if status in ("failed", "canceled"):
                return None
            time.sleep(3)
        return None


class FalImageToVideo:
    """Image-to-video via fal.ai (Wan / Kling i2v)."""

    name = "fal"

    def __init__(self, model: str = "fal-ai/wan/video/image-to-video",
                 timeout: int = 300):
        self.model = model
        self.timeout = timeout

    def animate(self, image_path: str, out_path: str, prompt: str = "",
                duration: float = 4.0) -> str:
        key = os.getenv("FAL_KEY")
        if not key:
            return None

        data_uri = _image_to_data_uri(image_path)
        body = {
            "image_url": data_uri,
            "prompt": prompt or "subtle camera movement, cinematic",
            "duration": str(max(1, int(round(duration)))) + "s",
        }
        headers = {"Authorization": f"Key {key}",
                   "Content-Type": "application/json"}
        url = f"https://fal.run/{self.model}"
        try:
            r = requests.post(url, json=body, headers=headers, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
        except Exception:  # pragma: no cover
            return None

        video_url = None
        video = data.get("video") or {}
        if isinstance(video, dict):
            video_url = video.get("url")
        if not video_url:
            out = data.get("output") or {}
            if isinstance(out, dict):
                video_url = out.get("url")
        if video_url and _download(video_url, out_path):
            return out_path
        return None


# ------------------------------------------------------------------ #

def get_motion_provider(name: str = "auto"):
    """Return a motion provider instance, or None if the name is unknown."""
    name = (name or "auto").lower()
    if name in ("replicate", "auto"):
        return ReplicateImageToVideo()
    if name == "fal":
        return FalImageToVideo()
    return None


def motion_provider_chain(explicit: str = None):
    """Ordered provider list for fallback. 'auto' tries Replicate then Fal."""
    if explicit and explicit.lower() != "auto":
        return [explicit.lower()]
    return ["replicate", "fal"]
