"""Prostudio v1 — FastAPI backend.

Wraps the ProstudioX pipeline (vendored under pipeline/) behind a REST + WebSocket
API so the Next.js frontend can drive generation with live progress.

Run:
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

import asyncio
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from jobs import create_job, get_job, job_events_after, list_jobs

app = FastAPI(title="Prostudio v1", version="1.0.0")

# CORS: allow the Next.js dev server + any localhost frontend.
# Tighten `allow_origins` to your production frontend origin when deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    topic: str
    script: str = ""
    voice: str = "en-US-GuyNeural"
    rate: str = "+0%"
    style: str = "cinematic"
    character: str = ""
    aspect_ratio: str = "9:16"
    image_provider: str = "auto"
    tts_provider: str = "auto"
    motion: bool = False
    motion_provider: str = "auto"
    motion_prompt: str = ""
    music_volume: float = 0.15
    openai_model: str = "gpt-4o-mini"
    use_supabase: bool = False
    keys: dict = Field(default_factory=dict)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Prostudio v1"}


@app.post("/api/generate")
def generate(req: GenerateRequest):
    if not req.topic.strip():
        raise HTTPException(status_code=422, detail="topic is required")
    _apply_keys(req.keys)
    options = req.model_dump(exclude={"topic", "keys"})
    job = create_job(req.topic.strip(), options)
    return {"job_id": job.id}


@app.get("/api/jobs")
def jobs():
    return [
        {"id": j.id, "topic": j.topic, "status": j.status, "step": j.step,
         "output_path": j.output_path, "public_url": j.public_url, "error": j.error}
        for j in list_jobs()
    ]


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    j = get_job(job_id)
    if j is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"id": j.id, "topic": j.topic, "status": j.status, "step": j.step,
            "output_path": j.output_path, "public_url": j.public_url, "error": j.error}


@app.get("/api/jobs/{job_id}/video")
def video(job_id: str):
    j = get_job(job_id)
    if j is None:
        raise HTTPException(status_code=404, detail="job not found")
    if not j.output_path or not os.path.exists(j.output_path):
        raise HTTPException(status_code=404, detail="video not ready")
    return FileResponse(j.output_path, media_type="video/mp4", filename="final.mp4")


@app.websocket("/ws/{job_id}")
async def ws(websocket: WebSocket, job_id: str):
    await websocket.accept()
    last_seq = 0
    try:
        j = get_job(job_id)
        if j is not None:
            await websocket.send_json({
                "type": "snapshot", "status": j.status, "step": j.step,
                "output_path": j.output_path, "public_url": j.public_url,
                "error": j.error,
            })
        while True:
            for e in job_events_after(job_id, last_seq):
                last_seq = max(last_seq, e["seq"])
                await websocket.send_json(e)
            j = get_job(job_id)
            if j is not None and j.status in ("done", "failed"):
                await websocket.send_json({"type": "end", "status": j.status})
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


def _apply_keys(keys: dict):
    """Fold optional client-supplied keys into the environment for this process."""
    if not keys:
        return
    for k, v in keys.items():
        if v:
            os.environ[k] = v
