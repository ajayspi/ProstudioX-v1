"""
ProstudioX — provider registry + fallback chains.

A single place to resolve image/TTS providers by name. `*_chain()` returns
the ordered list of provider names to try when `auto` (or an explicit first
choice) is requested, so a failed/absent provider degrades to the next one.
"""

# Image providers (free -> paid)
IMAGE_PROVIDERS = ["gemini", "pollinations", "huggingface", "together", "openai"]

# TTS providers (word-timestamps first)
TTS_PROVIDERS = ["edge", "gtts", "openai"]


def get_image_provider(name: str, **kwargs):
    name = (name or "").lower()
    if name == "gemini":
        from modules.gemini_image_generator import GeminiImageGenerator
        return GeminiImageGenerator(**kwargs)
    if name == "pollinations":
        from modules.pollinations_image_provider import PollinationsImageProvider
        return PollinationsImageProvider(**kwargs)
    if name == "huggingface":
        from modules.huggingface_image_provider import HuggingFaceImageProvider
        return HuggingFaceImageProvider(**kwargs)
    if name == "together":
        from modules.together_image_provider import TogetherImageProvider
        return TogetherImageProvider(**kwargs)
    if name == "openai":
        from modules.openai_image_provider import OpenAIImageProvider
        return OpenAIImageProvider(**kwargs)
    return None


def get_tts_provider(name: str, **kwargs):
    name = (name or "").lower()
    if name == "edge":
        from modules.tts_provider import TTSProvider
        return TTSProvider(**kwargs)
    if name == "gtts":
        from modules.gtts_provider import GoogleTranslateTTSProvider
        return GoogleTranslateTTSProvider(**kwargs)
    if name == "openai":
        from modules.openai_tts_provider import OpenAITTSProvider
        return OpenAITTSProvider(**kwargs)
    return None


def image_provider_chain(explicit: str = None):
    """Ordered provider names to try for images."""
    if explicit and explicit.lower() != "auto":
        return [explicit.lower()] + [p for p in IMAGE_PROVIDERS if p != explicit.lower()]
    return IMAGE_PROVIDERS


def tts_provider_chain(explicit: str = None):
    """Ordered provider names to try for TTS."""
    if explicit and explicit.lower() != "auto":
        return [explicit.lower()] + [p for p in TTS_PROVIDERS if p != explicit.lower()]
    return TTS_PROVIDERS
