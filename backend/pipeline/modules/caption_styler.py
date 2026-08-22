"""
Advanced Caption/Subtitle Styling System with Google Fonts
Provides extensive customization for video captions
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import streamlit as st


@dataclass
class CaptionStyle:
    """Caption styling configuration"""
    font_name: str = "Roboto"
    font_size: int = 40
    font_color: str = "#FFFFFF"  # Hex color
    background_color: str = "#000000"
    background_opacity: float = 0.7
    text_outline: bool = True
    outline_color: str = "#000000"
    outline_width: int = 2
    text_shadow: bool = True
    shadow_color: str = "#000000"
    shadow_offset: Tuple[int, int] = (2, 2)
    position: str = "bottom"  # top, center, bottom
    alignment: str = "center"  # left, center, right
    animation: str = "none"  # none, fade, slide, pop, typewriter
    animation_duration: float = 0.5
    line_spacing: float = 1.2
    bold: bool = False
    italic: bool = False
    uppercase: bool = False


class GoogleFontsProvider:
    """Fetch and manage Google Fonts"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GOOGLE_FONTS_API_KEY')
        self.base_url = "https://www.googleapis.com/webfonts/v1/webfonts"
        self.fonts_cache_file = Path("fonts_cache.json")
        self.fonts = self._load_fonts()

    def get_all_fonts(self, refresh: bool = False) -> List[Dict]:
        """Get all available Google Fonts"""

        # Use cache if available
        if self.fonts_cache_file.exists() and not refresh:
            with open(self.fonts_cache_file) as f:
                return json.load(f)

        if not self.api_key:
            st.warning("⚠️ GOOGLE_FONTS_API_KEY not configured. Using default fonts.")
            return self._get_default_fonts()

        try:
            params = {"key": self.api_key, "sort": "popularity"}
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()

            fonts = response.json().get("items", [])

            # Cache fonts
            with open(self.fonts_cache_file, 'w') as f:
                json.dump(fonts, f, indent=2)

            return fonts

        except Exception as e:
            st.warning(f"Could not fetch Google Fonts: {e}")
            return self._get_default_fonts()

    def _load_fonts(self) -> List[Dict]:
        """Load fonts from cache or API"""
        return self.get_all_fonts()

    def _get_default_fonts(self) -> List[Dict]:
        """Fallback default fonts (popular Google Fonts)"""
        return [
            {
                "family": "Roboto",
                "category": "sans-serif",
                "variants": ["400", "700", "400i", "700i"],
                "description": "Modern, clean sans-serif"
            },
            {
                "family": "Open Sans",
                "category": "sans-serif",
                "variants": ["400", "700"],
                "description": "Friendly and open sans-serif"
            },
            {
                "family": "Montserrat",
                "category": "sans-serif",
                "variants": ["400", "700", "900"],
                "description": "Bold, geometric sans-serif"
            },
            {
                "family": "Playfair Display",
                "category": "serif",
                "variants": ["400", "700"],
                "description": "Elegant, stylish serif"
            },
            {
                "family": "Lora",
                "category": "serif",
                "variants": ["400", "700"],
                "description": "Calligraphic serif font"
            },
            {
                "family": "Ubuntu",
                "category": "sans-serif",
                "variants": ["400", "700"],
                "description": "Humanist sans-serif"
            },
            {
                "family": "Poppins",
                "category": "sans-serif",
                "variants": ["400", "700", "900"],
                "description": "Geometric sans-serif"
            },
            {
                "family": "Raleway",
                "category": "sans-serif",
                "variants": ["400", "700"],
                "description": "Elegant sans-serif"
            },
            {
                "family": "Pacifico",
                "category": "handwriting",
                "variants": ["400"],
                "description": "Handwritten, friendly script"
            },
            {
                "family": "Dancing Script",
                "category": "handwriting",
                "variants": ["400", "700"],
                "description": "Elegant script font"
            },
            {
                "family": "Courier Prime",
                "category": "monospace",
                "variants": ["400", "700"],
                "description": "Monospace typewriter style"
            },
            {
                "family": "Merriweather",
                "category": "serif",
                "variants": ["400", "700"],
                "description": "Traditional serif font"
            },
            {
                "family": "Great Vibes",
                "category": "handwriting",
                "variants": ["400"],
                "description": "Cursive script font"
            },
            {
                "family": "Oswald",
                "category": "sans-serif",
                "variants": ["400", "700"],
                "description": "Condensed sans-serif"
            },
            {
                "family": "Source Sans Pro",
                "category": "sans-serif",
                "variants": ["400", "700"],
                "description": "Professional sans-serif"
            }
        ]

    def get_fonts_by_category(self, category: str) -> List[Dict]:
        """Get fonts filtered by category"""
        return [f for f in self.fonts if f.get("category") == category]

    def get_font_names(self) -> List[str]:
        """Get list of font names only"""
        return [f["family"] for f in self.fonts]


class CaptionStyler:
    """Apply styling to captions"""

    def __init__(self):
        self.styles_file = Path("caption_styles.json")
        self.presets = self._load_presets()

    def create_style(self, **kwargs) -> CaptionStyle:
        """Create a custom caption style"""
        return CaptionStyle(**{k: v for k, v in kwargs.items()
                               if hasattr(CaptionStyle, k)})

    def apply_style_to_video(self,
                            video_path: str,
                            captions: List[str],
                            style: CaptionStyle,
                            output_path: str) -> bool:
        """Apply caption style to video using FFmpeg"""

        try:
            import subprocess

            # Build FFmpeg filter for subtitles
            filter_str = self._build_ffmpeg_filter(captions, style)

            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', filter_str,
                '-c:a', 'copy',
                '-y',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                st.success("✅ Captions applied")
                return True
            else:
                st.error(f"FFmpeg error: {result.stderr}")
                return False

        except Exception as e:
            st.error(f"Error applying captions: {e}")
            return False

    def _build_ffmpeg_filter(self, captions: List[str], style: CaptionStyle) -> str:
        """Build FFmpeg drawtext filter for captions"""

        # Position mapping
        position_map = {
            "top": "y=10",
            "center": "y=(h-text_h)/2",
            "bottom": "y=h-text_h-10"
        }

        alignment_map = {
            "left": "x=10",
            "center": "x=(w-text_w)/2",
            "right": "x=w-text_w-10"
        }

        position = position_map.get(style.position, position_map["bottom"])
        alignment = alignment_map.get(style.alignment, alignment_map["center"])

        # Build drawtext parameters
        drawtext = (
            f"fontfile='fonts/{style.font_name}.ttf':"
            f"text='{captions[0]}':"
            f"fontsize={style.font_size}:"
            f"fontcolor={style.font_color}:"
            f"bordercolor={style.outline_color if style.text_outline else 'transparent'}:"
            f"borderw={style.outline_width if style.text_outline else 0}:"
            f"shadowcolor={style.shadow_color if style.text_shadow else 'transparent'}:"
            f"shadowx={style.shadow_offset[0] if style.text_shadow else 0}:"
            f"shadowy={style.shadow_offset[1] if style.text_shadow else 0}:"
            f"{alignment}:{position}"
        )

        return f"drawtext={drawtext}"

    def _load_presets(self) -> Dict[str, CaptionStyle]:
        """Load caption style presets"""
        return {
            "Classic Elegant": CaptionStyle(
                font_name="Great Vibes",
                font_size=48,
                font_color="#FFFFFF",
                background_color="#1a1a1a",
                text_outline=True,
                text_shadow=True,
                position="bottom",
                animation="fade"
            ),
            "Bold Modern": CaptionStyle(
                font_name="Montserrat",
                font_size=44,
                font_color="#FFFFFF",
                background_color="#000000",
                background_opacity=0.8,
                bold=True,
                text_outline=True,
                outline_width=3,
                position="bottom"
            ),
            "Elegant": CaptionStyle(
                font_name="Playfair Display",
                font_size=40,
                font_color="#FFD700",
                background_color="#1a1a1a",
                text_shadow=True,
                position="center",
                animation="slide"
            ),
            "Playful": CaptionStyle(
                font_name="Pacifico",
                font_size=36,
                font_color="#FF69B4",
                background_color="transparent",
                text_outline=True,
                outline_color="#FFFFFF",
                position="bottom",
                animation="pop"
            ),
            "Professional": CaptionStyle(
                font_name="Open Sans",
                font_size=38,
                font_color="#FFFFFF",
                background_color="#000000",
                background_opacity=0.6,
                position="bottom",
                alignment="center"
            ),
            "Cinematic": CaptionStyle(
                font_name="Raleway",
                font_size=42,
                font_color="#FFFFFF",
                background_color="#000000",
                background_opacity=0.7,
                text_shadow=True,
                shadow_offset=(3, 3),
                position="bottom",
                animation="fade",
                uppercase=True
            ),
            "Neon Glow": CaptionStyle(
                font_name="Poppins",
                font_size=40,
                font_color="#00FF00",
                background_color="#000000",
                text_outline=True,
                outline_color="#00FF00",
                outline_width=2,
                text_shadow=True,
                position="bottom"
            ),
            "Vintage": CaptionStyle(
                font_name="Courier Prime",
                font_size=36,
                font_color="#FFD700",
                background_color="#8B4513",
                background_opacity=0.5,
                text_outline=True,
                position="bottom"
            )
        }

    def get_preset(self, name: str) -> Optional[CaptionStyle]:
        """Get preset style by name"""
        return self.presets.get(name)

    def get_preset_names(self) -> List[str]:
        """Get list of all preset names"""
        return list(self.presets.keys())

    def save_custom_style(self, name: str, style: CaptionStyle):
        """Save custom caption style"""
        styles = self._load_saved_styles()
        styles[name] = style.__dict__
        with open(self.styles_file, 'w') as f:
            json.dump(styles, f, indent=2)
        st.success(f"✅ Saved style: {name}")

    def _load_saved_styles(self) -> Dict:
        """Load saved custom styles"""
        if self.styles_file.exists():
            with open(self.styles_file) as f:
                return json.load(f)
        return {}

    def get_saved_styles(self) -> List[str]:
        """Get list of saved custom styles"""
        return list(self._load_saved_styles().keys())


class ProstudioXCaptionPresets:
    """Specialized caption presets for ProstudioX professional video creation"""

    PRESETS = {
        "Finance Highlight": CaptionStyle(
            font_name="Playfair Display",
            font_size=44,
            font_color="#FFD700",
            background_color="#1a1a1a",
            background_opacity=0.8,
            text_shadow=True,
            shadow_color="#000000",
            shadow_offset=(2, 2),
            position="center",
            alignment="center",
            animation="fade",
            line_spacing=1.3
        ),
        "Professional Message": CaptionStyle(
            font_name="Open Sans",
            font_size=40,
            font_color="#FFFFFF",
            background_color="#1a1a2a",
            background_opacity=0.7,
            text_outline=True,
            outline_color="#00BFFF",
            outline_width=1,
            text_shadow=True,
            position="bottom",
            animation="fade"
        ),
        "Impact Title": CaptionStyle(
            font_name="Montserrat",
            font_size=48,
            font_color="#FFFFFF",
            background_color="#000000",
            background_opacity=0.8,
            bold=True,
            position="bottom",
            alignment="center",
            uppercase=True
        ),
        "Thought Caption": CaptionStyle(
            font_name="Lora",
            font_size=40,
            font_color="#E6E6FA",
            background_color="#2a2a4a",
            background_opacity=0.7,
            text_shadow=True,
            position="center",
            animation="slide",
            italic=True
        ),
        "Featured Title": CaptionStyle(
            font_name="Raleway",
            font_size=50,
            font_color="#FFFFFF",
            background_color="#000000",
            background_opacity=0.9,
            text_outline=True,
            outline_width=2,
            position="top",
            alignment="center",
            uppercase=True
        ),
        "Highlight Points": CaptionStyle(
            font_name="Poppins",
            font_size=42,
            font_color="#00FF88",
            background_color="transparent",
            text_shadow=True,
            shadow_color="#000000",
            shadow_offset=(3, 3),
            position="center",
            animation="pop",
            bold=True
        )
    }

    @classmethod
    def get_preset(cls, name: str) -> Optional[CaptionStyle]:
        return cls.PRESETS.get(name)

    @classmethod
    def get_all_presets(cls) -> Dict[str, CaptionStyle]:
        return cls.PRESETS.copy()

    @classmethod
    def get_preset_names(cls) -> List[str]:
        return list(cls.PRESETS.keys())
