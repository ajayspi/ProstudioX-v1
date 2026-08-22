"""
ProstudioX core modules package.

Complete end-to-end video generation pipeline:
  topic → script → TTS → images → music → assembly → upload

All components are optional-aware and degrade gracefully.
"""

from modules.tts_provider import TTSProvider, TTSResult, Word
from modules.gtts_provider import GoogleTranslateTTSProvider
from modules.openai_tts_provider import OpenAITTSProvider
from modules.video_processor import VideoProcessor
from modules.batch_manager import BatchProcessor, BatchResult, VideoJob
from modules.caption_styler import CaptionStyle, CaptionStyler, GoogleFontsProvider, ProstudioXCaptionPresets
from modules.supabase_client import SupabaseClient
from modules.pollinations_image_provider import PollinationsImageProvider
from modules.openai_image_provider import OpenAIImageProvider
from modules.huggingface_image_provider import HuggingFaceImageProvider
from modules.together_image_provider import TogetherImageProvider
from modules import provider_registry

__all__ = [
    # TTS
    "TTSProvider", "TTSResult", "Word", "GoogleTranslateTTSProvider", "OpenAITTSProvider",
    # Video
    "VideoProcessor",
    # Batch processing
    "BatchProcessor", "BatchResult", "VideoJob",
    # Captions
    "CaptionStyle", "CaptionStyler", "GoogleFontsProvider", "ProstudioXCaptionPresets",
    # Image providers
    "PollinationsImageProvider", "OpenAIImageProvider",
    "HuggingFaceImageProvider", "TogetherImageProvider",
    # Registry
    "provider_registry",
    # Storage
    "SupabaseClient",
]
