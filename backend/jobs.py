"""Prostudio v1 — background job runner + in-memory progress bus.

Each generation runs in a daemon thread. Progress events (status + per-step)
are appended to the job's event list and streamed to the frontend over WebSocket.
"""

import os
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

# Vendor the pipeline onto sys.path so `from modules...` resolves.
PIPELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline")
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from modules.batch_manager import BatchProcessor  # noqa: E402


@dataclass
class Job:
    id: str
    topic: str
    status: str = "queued"     # queued | running | done | failed
    step: str = "queued"       # queued | script | voice | images | music | render | done | failed
    output_path: str = ""
    public_url: str = ""
    error: str = ""
    created: float = field(default_factory=time.time)
    events: list = field(default_factory=list)
    seq: int = 0


_JOBS: dict = {}
_LOCK = threading.Lock()


def _emit(job_id: str, event_type: str, data: dict):
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        job.seq += 1
        job.events.append({"type": event_type, "seq": job.seq, "ts": time.time(), **data})


def create_job(topic: str, options: dict) -> Job:
    job_id = uuid.uuid4().hex[:12]
    job = Job(id=job_id, topic=topic)
    with _LOCK:
        _JOBS[job_id] = job
    threading.Thread(target=_run, args=(job_id, topic, options), daemon=True).start()
    return job


def _run(job_id: str, topic: str, options: dict):
    job = _JOBS[job_id]
    job.status = "running"
    _emit(job_id, "status", {"status": "running", "step": "starting"})
    try:
        bp = BatchProcessor(
            voice=options.get("voice", "en-US-GuyNeural"),
            rate=options.get("rate", "+0%"),
            out_root=options.get("out_root", "outputs"),
            music_volume=float(options.get("music_volume", 0.15)),
            use_supabase=bool(options.get("use_supabase", False)),
            openai_model=options.get("openai_model", "gpt-4o-mini"),
            image_provider=options.get("image_provider", "auto"),
            tts_provider=options.get("tts_provider", "auto"),
            style=options.get("style", "cinematic"),
            character=options.get("character", ""),
            aspect_ratio=options.get("aspect_ratio", "9:16"),
            motion=bool(options.get("motion", False)),
            motion_provider=options.get("motion_provider", "auto"),
            motion_prompt=options.get("motion_prompt", ""),
            on_step=lambda s: _on_step(job_id, s),
        )
        bp.add_video(topic, script=options.get("script", ""))

        def on_progress(j):
            _emit(job_id, "progress", {
                "status": j.status,
                "step": j.status,
                "output_path": j.output_path,
                "public_url": j.public_url,
                "elapsed": j.elapsed,
            })

        result = bp.process(on_progress=on_progress)
        finished = result.jobs[0]
        if finished.status == "done":
            job.status = "done"
            job.step = "done"
            job.output_path = finished.output_path
            job.public_url = finished.public_url
            _emit(job_id, "status", {"status": "done", "step": "done",
                                     "output_path": finished.output_path,
                                     "public_url": finished.public_url})
        else:
            job.status = "failed"
            job.step = "failed"
            job.error = finished.error
            _emit(job_id, "status", {"status": "failed", "step": "failed",
                                     "error": finished.error})
    except Exception as e:  # noqa: BLE001
        job.status = "failed"
        job.step = "failed"
        job.error = str(e)
        _emit(job_id, "status", {"status": "failed", "step": "failed", "error": str(e)})


def _on_step(job_id: str, step: str):
    job = _JOBS.get(job_id)
    if job is not None:
        job.step = step
    _emit(job_id, "step", {"step": step})


def get_job(job_id: str) -> Optional[Job]:
    return _JOBS.get(job_id)


def list_jobs() -> list:
    return list(_JOBS.values())


def job_events_after(job_id: str, after_seq: int) -> list:
    job = _JOBS.get(job_id)
    if job is None:
        return []
    with _LOCK:
        return [e for e in job.events if e["seq"] > after_seq]
