"""
ProstudioX — Video processor (ffmpeg assembly).

Turns a set of images + a voiceover (with word-level subtitles) + optional
background music into a finished vertical MP4.

Pipeline (two ffmpeg passes):
  1) images -> slideshow (Ken Burns zoom) -> silent video
  2) silent video + voiceover + ducked music + burned .ass subtitles -> mp4

Targets Linux/Colab. Requires ffmpeg on PATH.
"""

import os
import shutil
import subprocess


class VideoProcessor:
    def __init__(self, width: int = 1080, height: int = 1920, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("ffmpeg not found on PATH")

    # ------------------------------------------------------------------ #

    def assemble(self, images, audio_path, subtitle_path, output_path,
                 music_path=None, music_volume=0.15, image_duration=4.0,
                 crf=20, preset="medium") -> str:
        """Build the final video.

        images:        list of image file paths (local)
        audio_path:    voiceover mp3
        subtitle_path: .ass subtitle file (optional; word highlighting)
        output_path:   destination .mp4
        music_path:    optional background music mp3
        """
        images = [p for p in images if os.path.exists(p)]
        if not images:
            raise ValueError("No images provided (and none exist on disk)")
        if not os.path.exists(audio_path):
            raise ValueError(f"audio_path not found: {audio_path}")

        # Subtitles are optional (providers without word timestamps skip them)
        if subtitle_path and os.path.exists(subtitle_path):
            subtitle_path = os.path.abspath(subtitle_path)
        else:
            subtitle_path = None

        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

        work_dir = os.path.dirname(os.path.abspath(output_path))
        slideshow = os.path.join(work_dir, ".slideshow.mp4")

        self._build_slideshow(images, slideshow, image_duration)
        self._mux(slideshow, audio_path, subtitle_path, output_path,
                  music_path, music_volume, crf, preset)

        # cleanup intermediate
        if os.path.exists(slideshow):
            os.remove(slideshow)

        return output_path

    def assemble_clips(self, clips, audio_path, subtitle_path, output_path,
                       music_path=None, music_volume=0.15, crf=20,
                       preset="medium") -> str:
        """Build the final video from pre-rendered motion clips (no Ken Burns).

        clips:         list of video clip paths (local .mp4)
        audio_path:    voiceover mp3
        subtitle_path: .ass subtitle file (optional)
        """
        clips = [p for p in clips if os.path.exists(p)]
        if not clips:
            raise ValueError("No clips provided (and none exist on disk)")
        if not os.path.exists(audio_path):
            raise ValueError(f"audio_path not found: {audio_path}")

        if subtitle_path and os.path.exists(subtitle_path):
            subtitle_path = os.path.abspath(subtitle_path)
        else:
            subtitle_path = None

        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        work_dir = os.path.dirname(os.path.abspath(output_path))
        slideshow = os.path.join(work_dir, ".clips.mp4")

        self._concat_clips(clips, slideshow)
        self._mux(slideshow, audio_path, subtitle_path, output_path,
                  music_path, music_volume, crf, preset)

        if os.path.exists(slideshow):
            os.remove(slideshow)
        return output_path

    # ------------------------------------------------------------------ #

    def _build_slideshow(self, images, out_path, image_duration):
        """Single ffmpeg pass: each image -> zoompan clip -> concat."""
        inputs = []
        for p in images:
            inputs += ["-loop", "1", "-t", str(image_duration), "-i", p]

        filter_parts = []
        for i in range(len(images)):
            d_frames = int(image_duration * self.fps)
            vf = (
                f"scale={self.width}:{self.height}:force_original_aspect_ratio=increase,"
                f"crop={self.width}:{self.height},setsar=1,"
                f"zoompan=z='min(zoom+0.0008,1.12)':x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':d={d_frames}:s={self.width}x{self.height}:fps={self.fps}"
            )
            filter_parts.append(f"[{i}:v]{vf}[v{i}]")

        concat_inputs = "".join(f"[v{i}]" for i in range(len(images)))
        filter_parts.append(f"{concat_inputs}concat=n={len(images)}:v=1:a=0[vout]")

        cmd = (["ffmpeg", "-y"] + inputs +
               ["-filter_complex", ";".join(filter_parts),
                "-map", "[vout]", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "20", "-r", str(self.fps), out_path])
        self._run(cmd, "slideshow")

    def _concat_clips(self, clips, out_path):
        """Concat motion clips (scaled/cropped to canvas) into one silent video."""
        inputs = []
        for c in clips:
            inputs += ["-i", c]

        filter_parts = []
        for i in range(len(clips)):
            vf = (
                f"scale={self.width}:{self.height}:force_original_aspect_ratio=increase,"
                f"crop={self.width}:{self.height},setsar=1,fps={self.fps}"
            )
            filter_parts.append(f"[{i}:v]{vf}[v{i}]")

        concat_inputs = "".join(f"[v{i}]" for i in range(len(clips)))
        filter_parts.append(f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[vout]")

        cmd = (["ffmpeg", "-y"] + inputs +
               ["-filter_complex", ";".join(filter_parts),
                "-map", "[vout]", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "20", "-r", str(self.fps), out_path])
        self._run(cmd, "concat-clips")

    def _mux(self, slideshow, audio_path, subtitle_path, out_path,
             music_path, music_volume, crf, preset):
        """Second pass: combine video + voiceover (+ ducked music) + subtitles."""
        cmd = ["ffmpeg", "-y", "-i", slideshow, "-i", audio_path]
        if music_path and os.path.exists(music_path):
            cmd += ["-i", music_path]

        fc = []
        if music_path and os.path.exists(music_path):
            fc.append(f"[1:a]volume=1.0[tts]")
            fc.append(f"[2:a]volume={music_volume}[mus]")
            fc.append("[tts][mus]amix=inputs=2:duration=first:dropout_transition=0[aout]")
        else:
            fc.append("[1:a]anull[aout]")

        # Subtitles are optional (providers without word timestamps skip them)
        if subtitle_path:
            fc.append(f"[0:v]ass={self._ff_filter_path(subtitle_path)}[vout]")
        else:
            fc.append("[0:v]null[vout]")
        cmd += ["-filter_complex", ";".join(fc),
                "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                "-c:a", "aac", "-b:a", "192k", "-shortest", out_path]
        self._run(cmd, "mux")

    @staticmethod
    def _ff_filter_path(path: str) -> str:
        """Escape a path for use inside an ffmpeg filter string."""
        p = os.path.abspath(path).replace("\\", "/")
        p = p.replace(":", "\\:").replace("'", "\\'")
        return f"'{p}'"

    @staticmethod
    def _run(cmd, stage):
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"ffmpeg {stage} failed (exit {proc.returncode}):\n{proc.stderr[-2000:]}"
            )
