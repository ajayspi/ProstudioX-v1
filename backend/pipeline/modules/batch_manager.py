"""
ProstudioX — Batch manager (end-to-end pipeline orchestration).

Turns a list of topics into finished Shorts:

  topic -> script (OpenAI, optional) -> TTS (edge-tts -> gTTS -> OpenAI, fallback)
        -> images (Gemini -> Pollinations -> OpenAI, fallback)
        -> music (Pixabay, optional)
        -> assemble (ffmpeg) -> upload (Supabase Storage) -> record (Supabase)

Everything is optional-aware: if a provider (Gemini / Pollinations / Pixabay /
Supabase) is missing or fails, it degrades to the next provider and still
produces a video from what's there.

Usage:
    from modules.batch_manager import BatchProcessor
    bp = BatchProcessor(voice="en-US-GuyNeural")
    bp.add_video("3 money habits that quietly make you richer")
    bp.add_video("The 50/30/20 rule explained")
    results = bp.process(parallel=False)
"""

import os
import time
from dataclasses import dataclass, field

from modules.tts_provider import TTSProvider
from modules.video_processor import VideoProcessor

# Optional dependencies (imported lazily so the core still works without them)
try:
    from modules.supabase_client import SupabaseClient
except Exception:  # pragma: no cover
    SupabaseClient = None


@dataclass
class VideoJob:
    topic: str
    script: str = ""
    title: str = ""
    keywords: str = ""
    hashtags: str = ""
    status: str = "queued"          # queued | generating | done | failed
    output_path: str = ""
    public_url: str = ""
    error: str = ""
    elapsed: float = 0.0


@dataclass
class BatchResult:
    jobs: list = field(default_factory=list)
    done: int = 0
    failed: int = 0


FINANCE_PROMPT = """You are an expert personal-finance scriptwriter for 50-second
YouTube Shorts. Given a topic, produce a tight, retention-optimized script.

Return ONLY valid JSON with these keys:
  "title":   a clickable Short title (under 60 chars)
  "script":  the spoken script (~120-140 words, 50s at natural pace). Start with
             a hook, give 3 concrete points, end with a one-line call to action.
  "keywords": 6-8 comma-separated Pexels/Gemini search terms for B-roll (e.g.
             "money counting, coins, stock chart, calculator, wallet")
  "hashtags": 8-12 space-separated finance hashtags

Topic: {topic}
JSON:"""


class BatchProcessor:
    def __init__(self, voice: str = TTSProvider.DEFAULT_VOICE, rate: str = "+0%",
                 out_root: str = "outputs", image_duration: float = 4.0,
                 music_volume: float = 0.15, use_supabase: bool = False,
                 openai_model: str = "gpt-4o-mini",
                 image_provider: str = "auto", tts_provider: str = "auto",
                 style: str = "cinematic", character: str = "",
                 aspect_ratio: str = "9:16", motion: bool = False,
                 motion_provider: str = "auto", motion_prompt: str = "",
                 on_step=None):
        self.voice = voice
        self.rate = rate
        self.out_root = out_root
        self.image_duration = image_duration
        self.music_volume = music_volume
        self.openai_model = openai_model
        self.image_provider = image_provider
        self.tts_provider = tts_provider
        self.style = style
        self.character = character
        self.aspect_ratio = aspect_ratio
        self.motion = motion
        self.motion_provider = motion_provider
        self.motion_prompt = motion_prompt
        self.on_step = on_step

        from modules.style_presets import get_aspect
        self.width, self.height = get_aspect(aspect_ratio)
        self.video = VideoProcessor(width=self.width, height=self.height)

        self.sb = None
        if use_supabase and SupabaseClient is not None:
            self.sb = SupabaseClient()

        self.jobs: list[VideoJob] = []

    # ---------------------------------------------------------------- #

    def add_video(self, topic: str, script: str = "", title: str = "",
                  keywords: str = "", hashtags: str = ""):
        self.jobs.append(VideoJob(topic=topic, script=script, title=title,
                                  keywords=keywords, hashtags=hashtags))

    def _step(self, name: str):
        if self.on_step:
            try:
                self.on_step(name)
            except Exception:  # pragma: no cover
                pass

    # ---------------------------------------------------------------- #

    def process(self, parallel: bool = False, num_workers: int = 1,
                on_progress=None) -> BatchResult:
        """Run the queue. `parallel` is accepted for API compatibility;
        ffmpeg/TTS are sequential-safe by default (set num_workers > 1 only if
        you have the RAM/GPU)."""
        for job in self.jobs:
            self._process_one(job, on_progress)

        result = BatchResult(
            jobs=self.jobs,
            done=sum(1 for j in self.jobs if j.status == "done"),
            failed=sum(1 for j in self.jobs if j.status == "failed"),
        )
        return result

    def _process_one(self, job: VideoJob, on_progress):
        t0 = time.time()
        job.status = "generating"
        self._emit(on_progress, job)
        out_dir = os.path.join(self.out_root, self._slug(job.topic))

        try:
            self._step("script")
            # 1) Script (generate if not supplied)
            if not job.script:
                meta = self.generate_script(job.topic)
                job.script = meta.get("script", "")
                job.title = job.title or meta.get("title", job.topic)
                job.keywords = job.keywords or meta.get("keywords", "")
                job.hashtags = job.hashtags or meta.get("hashtags", "")
            if not job.script:
                raise RuntimeError("No script available (topic had no script)")

            self._step("voice")
            # 2) Voiceover (edge-tts -> gTTS -> OpenAI, with fallback)
            tts = self._synthesize_tts(job.script, out_dir)

            self._step("images")
            # 3) Images (Gemini if available, else a solid-color placeholder)
            images = self._make_images(job.keywords, out_dir)

            self._step("music")
            # 4) Background music (Pixabay if available)
            music = self._make_music(out_dir)

            self._step("render")
            # 5) Assemble (motion clips if enabled, else static Ken Burns)
            final = os.path.join(out_dir, "final.mp4")
            clips = self._animate_images(images, out_dir) if self.motion else []
            if clips:
                self.video.assemble_clips(
                    clips=clips, audio_path=tts.audio_path,
                    subtitle_path=tts.subtitle_path, output_path=final,
                    music_path=music, music_volume=self.music_volume,
                )
            else:
                self.video.assemble(
                    images=images, audio_path=tts.audio_path,
                    subtitle_path=tts.subtitle_path, output_path=final,
                    music_path=music, music_volume=self.music_volume,
                    image_duration=self.image_duration,
                )
            job.output_path = final

            # 6) Supabase (optional)
            if self.sb is not None:
                storage_path = f"{self._slug(job.topic)}/final.mp4"
                job.public_url = self.sb.upload_video(final, storage_path)
                self.sb.insert_video({
                    "topic": job.topic,
                    "script": job.script,
                    "title": job.title or job.topic,
                    "description": "",
                    "hashtags": job.hashtags,
                    "storage_path": storage_path,
                    "public_url": job.public_url,
                    "duration_seconds": int(tts.duration),
                    "status": "done",
                })

            job.status = "done"
        except Exception as e:  # noqa: BLE001
            job.status = "failed"
            job.error = str(e)
            if self.sb is not None:
                try:
                    self.sb.insert_video({"topic": job.topic, "status": "failed",
                                          "error": str(e)})
                except Exception:  # pragma: no cover
                    pass

        job.elapsed = round(time.time() - t0, 1)
        self._emit(on_progress, job)

    # ---------------------------------------------------------------- #
    #  Script generation (OpenAI)                                      #
    # ---------------------------------------------------------------- #

    def generate_script(self, topic: str) -> dict:
        import json
        try:
            import openai
        except ImportError:
            return {}

        api_key = os.getenv("OPENAI_API_KEY")
        if self.sb is not None:
            try:
                api_key = api_key or self.sb.get_secret("OPENAI_API_KEY")
            except Exception:  # pragma: no cover
                pass
        if not api_key:
            return {}

        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=self.openai_model,
            messages=[{"role": "user",
                       "content": FINANCE_PROMPT.format(topic=topic)}],
            temperature=0.7,
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw[raw.find("{"):raw.rfind("}") + 1]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"script": raw}

    # ---------------------------------------------------------------- #
    #  Images & music (optional providers, graceful fallback)           #
    # ---------------------------------------------------------------- #

    def _make_images(self, keywords, out_dir):
        from modules.style_presets import get_style
        img_dir = os.path.join(out_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        prompts = [p.strip() for p in (keywords or "").split(",") if p.strip()][:8]
        if not prompts:
            return self._placeholder_images(out_dir, 6)

        # Enrich every prompt with an optional consistent character + style look.
        style_suffix = get_style(self.style)
        enriched = []
        for kw in prompts:
            parts = []
            if self.character:
                parts.append(self.character)
            parts.append(kw)
            if style_suffix:
                parts.append(style_suffix)
            enriched.append(", ".join(parts))

        from modules import provider_registry
        for provider_name in provider_registry.image_provider_chain(self.image_provider):
            provider = provider_registry.get_image_provider(provider_name)
            if provider is None:
                continue
            # Keep provider dimensions in sync with the chosen aspect ratio.
            if hasattr(provider, "width"):
                provider.width = self.width
            if hasattr(provider, "height"):
                provider.height = self.height
            try:
                results = provider.generate_batch_images(
                    enriched, style=None, content_theme=False)
                paths = []
                for i, (_prompt, img) in enumerate(results):
                    if img is not None:
                        p = os.path.join(img_dir, f"{provider_name}_{i:02d}.png")
                        img.save(p)
                        paths.append(p)
                if paths:
                    return paths
            except Exception:  # pragma: no cover
                continue
        return self._placeholder_images(out_dir, len(prompts))

    def _synthesize_tts(self, text, out_dir):
        """Try TTS providers in order; return the first that succeeds."""
        from modules import provider_registry
        errors = []
        for provider_name in provider_registry.tts_provider_chain(self.tts_provider):
            try:
                if provider_name == "edge":
                    from modules.tts_provider import TTSProvider
                    provider = TTSProvider(voice=self.voice, rate=self.rate)
                else:
                    provider = provider_registry.get_tts_provider(provider_name)
                if provider is None:
                    continue
                return provider.synthesize(text, out_dir, base_name="voice")
            except Exception as e:  # noqa: BLE001
                errors.append(f"{provider_name}: {e}")
                continue
        raise RuntimeError("All TTS providers failed: " + "; ".join(errors))

    def _placeholder_images(self, out_dir, count):
        """Solid-color fallback frames so assembly always succeeds."""
        from PIL import Image
        img_dir = os.path.join(out_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        paths = []
        colors = [(10, 14, 39), (26, 31, 58), (45, 20, 30), (20, 40, 30),
                  (50, 30, 10), (25, 25, 50)]
        for i in range(count):
            img = Image.new("RGB", (self.width, self.height), colors[i % len(colors)])
            p = os.path.join(img_dir, f"frame_{i:02d}.png")
            img.save(p)
            paths.append(p)
        return paths

    def _animate_images(self, images, out_dir):
        """Optionally convert static images to motion clips.

        All-or-nothing per provider: if any clip fails, fall back to static
        (return []). No API key / all providers fail => [] as well.
        """
        from modules import image_to_video
        clip_dir = os.path.join(out_dir, "clips")
        os.makedirs(clip_dir, exist_ok=True)
        for provider_name in image_to_video.motion_provider_chain(self.motion_provider):
            provider = image_to_video.get_motion_provider(provider_name)
            if provider is None:
                continue
            clips = []
            ok = True
            for i, img in enumerate(images):
                clip = os.path.join(clip_dir, f"clip_{i:02d}.mp4")
                try:
                    result = provider.animate(img, clip, prompt=self.motion_prompt,
                                              duration=self.image_duration)
                except Exception:  # pragma: no cover
                    result = None
                if result and os.path.exists(result):
                    clips.append(result)
                else:
                    ok = False
                    break
            if ok and clips:
                return clips
            # provider failed partway or returned nothing; try the next one
        return []

    def _make_music(self, out_dir):
        try:
            from modules.music_provider import PixabayMusicProvider
            music = PixabayMusicProvider()
            # valid moods: peaceful/corporate/inspirational/uplifting/cinematic/nature/ambient
            results = music.search_music(mood="cinematic")
            if results:
                # download_music(music_id, music_data) -> str path (or None)
                return music.download_music(results[0]["id"], results[0])
        except Exception:  # pragma: no cover
            pass
        return None

    # ---------------------------------------------------------------- #

    @staticmethod
    def _slug(topic: str) -> str:
        import re
        s = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
        return s[:60] or "video"

    @staticmethod
    def _emit(on_progress, job):
        if on_progress:
            on_progress(job)
