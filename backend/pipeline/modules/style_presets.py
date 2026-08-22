"""
ProstudioX — style presets, aspect ratios & consistent characters.

Curated look presets (inspired by Higgsfield's Viral Presets / AI styles and
Vadoo's AI styles) so every image in a Short shares a deliberate visual
identity instead of defaulting to a generic look.
"""

# name -> rich prompt suffix (appended to every image prompt)
STYLE_PRESETS = {
    "cinematic": (
        "cinematic lighting, shallow depth of field, film grain, dramatic "
        "composition, photorealistic, 35mm"
    ),
    "photographic": (
        "professional stock photography, natural lighting, sharp focus, "
        "ultra realistic, high detail"
    ),
    "minimal": (
        "clean minimal composition, soft studio lighting, lots of negative "
        "space, premium editorial aesthetic"
    ),
    "dark": (
        "dark moody atmosphere, high contrast, dramatic shadows, cinematic noir"
    ),
    "documentary": (
        "documentary realism, candid natural lighting, authentic texture, editorial"
    ),
    "3d render": (
        "3D render, octane render, soft studio lighting, high detail, depth of field"
    ),
    "flat illustration": (
        "flat vector illustration, bold clean shapes, modern editorial, vibrant palette"
    ),
    "isometric": (
        "isometric 3D illustration, clean, modern, soft shadows, premium"
    ),
    "retro": (
        "retro vintage aesthetic, film photography, warm faded tones, subtle grain"
    ),
    "neon": (
        "neon-lit futuristic, vibrant glow, high contrast, cyberpunk mood"
    ),
}

# name -> (width, height)
ASPECT_RATIOS = {
    "9:16": (1080, 1920),   # Shorts / Reels / TikTok
    "16:9": (1920, 1080),   # YouTube standard
    "1:1": (1080, 1080),    # square feed
    "4:5": (1080, 1350),    # portrait feed
}

# Suggested consistent-character presets (finance faceless personas).
# The chosen description is prepended to every image prompt so the same
# "host" appears across all scenes. Empty string = pure B-roll (default).
CHARACTER_PRESETS = {
    "none": "",
    "host": (
        "a confident professional presenter in business-casual attire, warm "
        "expression, studio background"
    ),
    "minimal narrator": (
        "a minimalist faceless figure, clean silhouette, neutral studio backdrop"
    ),
    "hands-on desk": (
        "close-up of hands writing on a desk with charts and a calculator nearby"
    ),
}


def get_style(style: str) -> str:
    """Return the rich style suffix for a preset name (or the name itself if unknown)."""
    return STYLE_PRESETS.get(style, style)


def get_aspect(aspect_ratio: str):
    """Return (width, height) for an aspect ratio name. Default 9:16."""
    return ASPECT_RATIOS.get(aspect_ratio, ASPECT_RATIOS["9:16"])
