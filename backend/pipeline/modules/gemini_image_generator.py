import os
import base64
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple
import google.generativeai as genai
import streamlit as st
from PIL import Image
import io

class GeminiImageGenerator:
    """Generate images using Google Gemini API for video creation"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.cache_dir = Path("generated_images")
        self.cache_dir.mkdir(exist_ok=True)
        self.manifest_file = self.cache_dir / "manifest.json"

    def generate_image(self,
                      prompt: str,
                      style: str = "cinematic",
                      content_theme: bool = True) -> Optional[Image.Image]:
        """Generate image using Gemini with professional styling"""

        # Enhance prompt with style/theme context
        enhanced_prompt = self._enhance_prompt(prompt, style, content_theme)

        try:
            response = self.model.generate_images(
                prompt=enhanced_prompt,
                number_of_images=1,
                size="1080x1920"  # Vertical format for Reels/Shorts
            )

            if response and len(response) > 0:
                image = response[0]
                self._save_to_cache(prompt, image, style)
                return image

            return None
        except Exception as e:
            st.error(f"Error generating image: {e}")
            return None

    def generate_batch_images(self,
                            prompts: List[str],
                            style: str = "cinematic",
                            content_theme: bool = True) -> List[Tuple[str, Optional[Image.Image]]]:
        """Generate multiple images for video sequence"""

        results = []
        progress_bar = st.progress(0)

        for idx, prompt in enumerate(prompts):
            image = self.generate_image(prompt, style, content_theme)
            results.append((prompt, image))
            progress_bar.progress((idx + 1) / len(prompts))

        return results

    def _enhance_prompt(self, base_prompt: str, style: str, content_theme: bool) -> str:
        """Enhance prompt with artistic direction"""

        style_modifiers = {
            "cinematic": "cinematic lighting, professional photography, dramatic, high quality, 4K",
            "painting": "oil painting style, artistic, beautiful brushstrokes, museum quality",
            "abstract": "abstract art, modern, flowing colors, surreal, dreamy",
            "nature": "nature photography, landscapes, golden hour, serene, peaceful",
            "corporate": "clean professional corporate imagery, modern financial visuals, trustworthy, high quality"
        }

        theme_modifiers = {
            True: "clean professional finance visuals, modern and trustworthy, suitable for money and investing content",
            False: ""
        }

        style_text = style_modifiers.get(style, style_modifiers["cinematic"])
        theme_text = theme_modifiers.get(content_theme, "")

        enhanced = f"{base_prompt}\n\n{style_text}"
        if theme_text:
            enhanced += f"\n{theme_text}"

        enhanced += "\n\nVertical composition (1080x1920), suitable for short-form video"

        return enhanced

    def _save_to_cache(self, prompt: str, image: Image.Image, style: str):
        """Save generated image to cache"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gemini_{timestamp}_{hash(prompt) % 10000}.png"
            filepath = self.cache_dir / filename

            # Save image
            image.save(filepath)

            # Update manifest
            manifest = self._load_manifest()
            manifest['images'].append({
                'filename': filename,
                'prompt': prompt,
                'style': style,
                'created_at': datetime.now().isoformat(),
                'size_mb': os.path.getsize(filepath) / (1024 * 1024)
            })

            with open(self.manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)

        except Exception as e:
            st.warning(f"Could not cache image: {e}")

    def _load_manifest(self) -> dict:
        """Load image manifest"""
        if self.manifest_file.exists():
            with open(self.manifest_file) as f:
                return json.load(f)
        return {'images': []}

    def get_cached_images(self) -> List[dict]:
        """Get all cached generated images"""
        return self._load_manifest().get('images', [])

    def get_image_path(self, filename: str) -> Optional[str]:
        """Get path to cached image"""
        path = self.cache_dir / filename
        return str(path) if path.exists() else None


class ImageSequenceToVideo:
    """Convert image sequence to video with transitions and animation"""

    def __init__(self):
        self.temp_dir = Path("temp_frames")
        self.temp_dir.mkdir(exist_ok=True)

    def create_video_from_images(self,
                                images: List[Image.Image],
                                duration_per_image: float = 3.0,
                                transition: str = "fade",
                                fps: int = 30,
                                output_path: str = "output.mp4") -> bool:
        """Create video from image sequence"""

        try:
            import cv2
            import numpy as np

            # Prepare video writer
            height, width = 1920, 1080
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            frames_per_image = int(duration_per_image * fps)
            total_frames = len(images) * frames_per_image
            progress_bar = st.progress(0)

            for idx, img in enumerate(images):
                # Convert PIL to OpenCV format
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                img_cv = cv2.resize(img_cv, (width, height))

                # Apply transition effect
                if transition == "fade" and idx > 0:
                    alpha_step = 1.0 / frames_per_image
                    for frame_idx in range(frames_per_image):
                        alpha = frame_idx * alpha_step
                        blended = cv2.addWeighted(img_cv, alpha, img_cv, 1-alpha, 0)
                        out.write(blended.astype(np.uint8))
                else:
                    # Regular frames
                    for _ in range(frames_per_image):
                        out.write(img_cv)

                progress = (idx + 1) * frames_per_image / total_frames
                progress_bar.progress(min(progress, 0.99))

            out.release()
            progress_bar.progress(1.0)
            return True

        except Exception as e:
            st.error(f"Error creating video: {e}")
            return False

    def add_text_overlay(self,
                        video_path: str,
                        texts: List[str],
                        font_size: int = 40,
                        output_path: str = "output_with_text.mp4") -> bool:
        """Add text overlays to video"""

        try:
            import cv2

            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            frame_count = 0
            text_idx = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Add text every 90 frames (3 seconds at 30fps)
                if frame_count % 90 == 0 and text_idx < len(texts):
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    text = texts[text_idx]

                    # Center text
                    text_size = cv2.getTextSize(text, font, font_size/10, 2)[0]
                    x = (width - text_size[0]) // 2
                    y = height - 100

                    # Add semi-transparent background
                    cv2.rectangle(frame,
                                (x-10, y-40),
                                (x+text_size[0]+10, y+20),
                                (0, 0, 0), -1)

                    cv2.putText(frame, text, (x, y),
                              font, font_size/10, (255, 255, 255), 2)

                    text_idx += 1

                out.write(frame)
                frame_count += 1

            cap.release()
            out.release()
            return True

        except Exception as e:
            st.error(f"Error adding text overlay: {e}")
            return False


# Example finance image prompts for ProstudioX
FINANCE_IMAGE_PROMPTS = {
    "saving": [
        "Coins stacking into a growing pile, warm studio lighting",
        "Piggy bank with coins being dropped in, clean background",
        "Person putting cash into a savings jar at a tidy desk"
    ],
    "investing": [
        "Rising stock chart on a sleek screen, green upward trend",
        "Diversified investment portfolio visualized as growing bars",
        "Candlestick chart with upward momentum, dark professional theme"
    ],
    "budgeting": [
        "Clean spreadsheet with budget categories on a laptop",
        "Calculator next to neatly organized bills and receipts",
        "Person reviewing a monthly budget with a focused expression"
    ],
    "wealth": [
        "Growing wealth visualized as ascending steps of gold coins",
        "Sunrise over a city skyline, symbolizing financial growth",
        "Hands holding a sprouting plant with coins, growth and prosperity"
    ]
}
