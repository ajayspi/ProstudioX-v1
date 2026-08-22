"""
Royalty-free music integration for ProstudioX videos
Supports: Pixabay Music API (free, no credit required)
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import streamlit as st

class MusicProvider:
    """Base class for music providers"""

    def search_music(self, query: str, mood: str, duration: int) -> List[Dict]:
        raise NotImplementedError

    def download_music(self, music_id: str, output_path: str) -> bool:
        raise NotImplementedError


class PixabayMusicProvider(MusicProvider):
    """Pixabay Music API integration - FREE, no attribution required"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('PIXABAY_MUSIC_API_KEY')
        self.base_url = "https://pixabay.com/api/videos/"
        self.cache_dir = Path("music_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.manifest_file = self.cache_dir / "manifest.json"

    def search_music(self,
                    mood: str = "peaceful",
                    category: str = "ambient",
                    min_duration: int = 0,
                    max_duration: int = 600) -> List[Dict]:
        """Search Pixabay for royalty-free music"""

        # Map moods to search terms
        mood_queries = {
            "peaceful": "calm peaceful ambient",
            "corporate": "corporate business finance",
            "inspirational": "inspirational uplifting motivation",
            "uplifting": "uplifting positive energy",
            "cinematic": "cinematic dramatic epic",
            "nature": "nature ambient forest",
            "ambient": "ambient focus productivity"
        }

        query = mood_queries.get(mood, mood)

        try:
            params = {
                "key": self.api_key,
                "q": query,
                "per_page": 50,
                "order": "popular"
            }

            response = requests.get(self.base_url, params=params)
            response.raise_for_status()

            results = response.json().get("hits", [])

            # Filter by duration
            filtered = []
            for item in results:
                # Get video duration (Pixabay returns videos, extract audio info)
                if "duration" in item:
                    duration = item.get("duration", 0)
                    if min_duration <= duration <= max_duration:
                        filtered.append({
                            "id": item.get("id"),
                            "title": item.get("tags", "Untitled"),
                            "duration": duration,
                            "user": item.get("user", "Pixabay"),
                            "preview_url": item.get("videos", {}).get("tiny", {}).get("url"),
                            "download_url": item.get("videos", {}).get("large", {}).get("url"),
                            "source": "Pixabay Music"
                        })

            return filtered[:20]  # Return top 20

        except Exception as e:
            st.error(f"Error searching Pixabay Music: {e}")
            return []

    def download_music(self, music_id: str, music_data: Dict) -> Optional[str]:
        """Download music from Pixabay"""

        try:
            download_url = music_data.get("download_url")
            if not download_url:
                st.error("No download URL available")
                return None

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"music_{music_id}_{timestamp}.mp4"
            filepath = self.cache_dir / filename

            # Download file
            with st.spinner(f"📥 Downloading music..."):
                response = requests.get(download_url, stream=True)
                response.raise_for_status()

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            # Add to manifest
            self._add_to_manifest(filename, music_data)

            st.success(f"✅ Downloaded: {music_data.get('title')}")
            return str(filepath)

        except Exception as e:
            st.error(f"Error downloading music: {e}")
            return None

    def _add_to_manifest(self, filename: str, music_data: Dict):
        """Add downloaded music to manifest"""
        manifest = self._load_manifest()

        manifest['music'].append({
            'filename': filename,
            'title': music_data.get('title'),
            'duration': music_data.get('duration'),
            'user': music_data.get('user'),
            'source': 'Pixabay Music',
            'downloaded_at': datetime.now().isoformat(),
            'size_mb': os.path.getsize(self.cache_dir / filename) / (1024 * 1024)
        })

        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

    def _load_manifest(self) -> dict:
        """Load music manifest"""
        if self.manifest_file.exists():
            with open(self.manifest_file) as f:
                return json.load(f)
        return {'music': []}

    def get_cached_music(self) -> List[Dict]:
        """Get all cached music"""
        return self._load_manifest().get('music', [])


class AudioProcessor:
    """Process and blend audio with video"""

    def __init__(self):
        pass

    def merge_audio_with_video(self,
                              video_path: str,
                              audio_path: str,
                              output_path: str,
                              audio_volume: float = 0.7) -> bool:
        """Merge audio (music) with video file"""

        try:
            import subprocess

            # FFmpeg command to merge audio
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                '-y',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                st.success("✅ Audio merged with video")
                return True
            else:
                st.error(f"FFmpeg error: {result.stderr}")
                return False

        except Exception as e:
            st.error(f"Error merging audio: {e}")
            return False

    def add_voiceover(self,
                     video_path: str,
                     audio_path: str,
                     voiceover_path: str,
                     output_path: str,
                     music_volume: float = 0.5,
                     voiceover_volume: float = 1.0) -> bool:
        """Blend background music with voiceover (ducking)"""

        try:
            import subprocess

            # FFmpeg filter_complex for audio ducking
            filter_complex = f"""
            [1:a]volume={music_volume}[music];
            [2:a]volume={voiceover_volume}[voice];
            [music][voice]amix=inputs=2:duration=first[audio]
            """

            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', audio_path,
                '-i', voiceover_path,
                '-filter_complex', filter_complex,
                '-map', '0:v:0',
                '-map', '[audio]',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-y',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                st.success("✅ Audio blended (music + voiceover)")
                return True
            else:
                st.error(f"FFmpeg error: {result.stderr}")
                return False

        except Exception as e:
            st.error(f"Error blending audio: {e}")
            return False

    def apply_audio_effects(self,
                           audio_path: str,
                           effect: str = "fade",
                           duration: float = 2.0,
                           output_path: str = "output_audio.mp3") -> bool:
        """Apply audio effects (fade in/out, normalize)"""

        try:
            import subprocess

            effects = {
                "fade_in": f"afade=t=in:st=0:d={duration}",
                "fade_out": f"afade=t=out:st=0:d={duration}",
                "normalize": "anormalize=1.0"
            }

            filter_str = effects.get(effect, "anull")

            cmd = [
                'ffmpeg',
                '-i', audio_path,
                '-af', filter_str,
                '-y',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                st.success(f"✅ Applied {effect} effect")
                return True
            else:
                st.error(f"FFmpeg error: {result.stderr}")
                return False

        except Exception as e:
            st.error(f"Error applying audio effects: {e}")
            return False


class MusicLibrary:
    """Curated music library for ProstudioX finance content"""

    CURATED_TRACKS = {
        "corporate_confident": {
            "title": "Market Momentum",
            "mood": "corporate",
            "tempo": "moderate",
            "duration": 180,
            "best_for": "investing, market updates, financial news",
            "description": "Clean, confident corporate backdrop"
        },
        "ambient_focus": {
            "title": "Wealth Mindset",
            "mood": "peaceful",
            "tempo": "slow",
            "duration": 200,
            "best_for": "budgeting, saving, personal finance tips",
            "description": "Calm, focused ambient track"
        },
        "motivational_growth": {
            "title": "Growth Trajectory",
            "mood": "inspirational",
            "tempo": "moderate",
            "duration": 240,
            "best_for": "success stories, side hustles, motivation",
            "description": "Uplifting, optimistic energy"
        },
        "cinematic_opportunity": {
            "title": "Big Opportunity",
            "mood": "cinematic",
            "tempo": "moderate",
            "duration": 210,
            "best_for": "real estate, entrepreneurship, wealth building",
            "description": "Dramatic, high-stakes atmosphere"
        },
        "uplifting_achievement": {
            "title": "Win The Day",
            "mood": "uplifting",
            "tempo": "fast",
            "duration": 190,
            "best_for": "debt payoff, milestones, wins",
            "description": "Energetic, triumphant, empowering"
        }
    }

    @classmethod
    def get_recommended_music(cls, content_type: str) -> Optional[Dict]:
        """Get recommended music for content type"""

        recommendations = {
            "investing": cls.CURATED_TRACKS["corporate_confident"],
            "budgeting": cls.CURATED_TRACKS["ambient_focus"],
            "motivation": cls.CURATED_TRACKS["motivational_growth"],
            "entrepreneurship": cls.CURATED_TRACKS["cinematic_opportunity"],
            "milestones": cls.CURATED_TRACKS["uplifting_achievement"]
        }

        return recommendations.get(content_type)

    @classmethod
    def list_all_tracks(cls) -> Dict:
        """List all available tracks"""
        return cls.CURATED_TRACKS

    @classmethod
    def search_tracks(cls, mood: str = None, tempo: str = None) -> List[Dict]:
        """Search tracks by mood or tempo"""

        results = []

        for track_id, track in cls.CURATED_TRACKS.items():
            if mood and track.get('mood') != mood:
                continue
            if tempo and track.get('tempo') != tempo:
                continue

            results.append({
                'id': track_id,
                **track
            })

        return results
