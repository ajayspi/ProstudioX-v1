# Free Platforms for Images, TTS, and Video

A catalog of free/cheap providers wired (or wireable) into ProstudioX.
Status verified 2026-08-22.

## Image generation (free / keyless first)

| Provider | Cost | API key? | Status in ProstudioX | Notes |
|----------|------|----------|----------------------|-------|
| [Pollinations.ai](https://pollinations.ai) | Free, unlimited | **No** | ✅ `pollinations_image_provider.py` | Plain URL: `image.pollinations.ai/prompt/<prompt>`. Models: flux, gptimage, seedream. |
| [Google Gemini](https://ai.google.dev) | Free tier | Yes (GEMINI_API_KEY) | ✅ `gemini_image_generator.py` | Existing provider; free tier via Google AI Studio. |
| [OpenAI gpt-image-1 / DALL-E](https://platform.openai.com) | Pay-per-use (your key) | Yes (OPENAI_API_KEY) | ✅ `openai_image_provider.py` | Uses your existing OpenAI key. |
| [Together AI](https://www.together.ai) | Free tier | Yes (TOGETHER_API_KEY) | ✅ `together_image_provider.py` | FLUX.1-schnell (free) via images API. |
| [Hugging Face Inference](https://huggingface.co/inference-api) | Free tier | Yes (HF token) | ✅ `huggingface_image_provider.py` | FLUX.1-schnell/dev, SDXL, etc. |
| Stable Diffusion / FLUX (local) | Free | No | ⬜ not wired | Heavy (GPU); not worth it for this use case. |

## Text-to-speech (free / keyless first)

| Provider | Cost | API key? | Word timestamps? | Status |
|----------|------|----------|------------------|--------|
| [edge-tts](https://github.com/rany2/edge-tts) | Free | **No** | ✅ Yes | ✅ `tts_provider.py` (primary, word-highlighted captions) |
| [gTTS](https://pypi.org/project/gTTS/) | Free | **No** | ❌ No | ✅ `gtts_provider.py` (fallback) |
| [StreamElements TTS](https://streamelements.com/dashboard/tts) | Free | **No** | ❌ No | ⬜ not wired (Google Wavenet voices) |
| [OpenAI TTS](https://platform.openai.com/docs/guides/text-to-speech) | Pay-per-use (your key) | Yes | ❌ No | ✅ `openai_tts_provider.py` |
| Coqui TTS / Piper (local) | Free | No | ✅ Yes | ⬜ not wired (heavy / local models) |

## Video (image-to-video / motion)

| Provider | Cost | API key? | Status |
|----------|------|----------|--------|
| [Replicate — Wan 2.1 i2v](https://replicate.com) | Free signup credits, then pay-per-use | Yes (`REPLICATE_API_TOKEN`) | ✅ `image_to_video.py` (default motion provider) |
| [fal.ai — Wan/Kling i2v](https://fal.ai) | Free credits, then pay-per-use | Yes (`FAL_KEY`) | ✅ `image_to_video.py` (fallback) |
| [Pollinations.ai](https://pollinations.ai) | Free | No | ⬜ not wired — Pollinations also serves text/image/**video** models over the same API |
| Stable Video Diffusion (local) | Free | No | ⬜ not wired (needs GPU) |

Motion is **off by default** — without `--motion`, ProstudioX uses the classic
Ken Burns zoom on stills. Enable it to animate each image into a clip; if a
provider is missing a key or any clip fails, it falls back to static automatically.

## How providers are selected

`batch_manager.py` tries providers **in order** and falls back to the next one
that works. Defaults:

- Images: `gemini` → `pollinations` → `huggingface` → `together` → `openai` → placeholder frames
- TTS: `edge` → `gtts` → `openai`
- Motion (optional): `replicate` → `fal` → static Ken Burns

Force a specific provider with the CLI:

```bash
python generate.py --topic "3 money habits" --image-provider pollinations
python generate.py --topic "3 money habits" --tts-provider gtts
python generate.py --topic "3 money habits" --motion --motion-provider replicate
```

`pollinations` + `gtts` are the two that need **zero API keys** — the fastest
way to get a first render without configuring anything.

## Sources

- Pollinations.ai — "One API for text, image, audio, video" (https://pollinations.ai)
- Eden AI — "Pollinations.ai is the simplest option when no API key required" (https://www.edenai.co/post/top-free-image-generation-tools-apis-and-open-source-models)
- Together AI — "Free endpoint for the SOTA open-source image generation model" (https://www.together.ai/models/flux-1-schnell)
- Hugging Face — "Inference Providers includes a generous free tier" (https://huggingface.co/docs/inference-providers/en/index)
- edge-tts — "Free, 74 languages, 322 voices, no registration" (https://edge-tts.com)
