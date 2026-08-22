# Prostudio v1

Turn a topic into a finished faceless finance Short (9:16 MP4) with a smooth,
modern web UI — script → voiceover → AI images → music → ffmpeg render, with
live per-step progress.

This is a rebuilt frontend + backend for the ProstudioX pipeline:

- **Backend** — FastAPI (Python), wraps the existing pipeline (vendored under
  `backend/pipeline/`), runs generation in a background thread, and streams
  progress over WebSocket.
- **Frontend** — Next.js (App Router) + Tailwind CSS + Framer Motion +
  shadcn-style components.

## Stack

| Layer | Tool |
|-------|------|
| Frontend | Next.js 14 (React 18) + Tailwind CSS |
| Animation | Framer Motion |
| UI components | shadcn-style (hand-written, zero Radix deps) |
| Backend | FastAPI |
| Live progress | WebSocket |
| Pipeline | ProstudioX modules (edge-tts / gTTS / Pollinations / HF / Together / OpenAI / Pixabay / ffmpeg) |

## Project structure

```
Prostudio-v1/
├── backend/
│   ├── main.py            # FastAPI app (REST + WebSocket)
│   ├── jobs.py            # background job runner + progress bus
│   ├── requirements.txt
│   ├── .env.example
│   └── pipeline/          # vendored ProstudioX pipeline
│       ├── modules/
│       └── generate.py
└── frontend/
    ├── app/               # page.tsx, layout.tsx, globals.css
    ├── components/
    │   ├── ui/            # button, card, input, select, switch, progress, …
    │   └── pipeline-progress.tsx
    └── lib/               # api.ts, utils.ts
```

## Quickstart

### 1. Backend (port 8000)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# system requirement: ffmpeg (Ubuntu: sudo apt install -y ffmpeg)
cp .env.example .env          # optional: add your keys
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend (port 3000)

```bash
cd frontend
npm install
cp .env.local.example .env.local    # points at http://localhost:8000 by default
npm run dev
```

Open http://localhost:3000.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | health check |
| POST | `/api/generate` | start a generation job (JSON body, see below) |
| GET | `/api/jobs` | list jobs |
| GET | `/api/jobs/{id}` | job status |
| GET | `/api/jobs/{id}/video` | download the finished MP4 |
| WS | `/ws/{id}` | live progress stream |

### `/api/generate` body

```json
{
  "topic": "3 money habits that quietly make you richer",
  "script": "",
  "voice": "en-US-GuyNeural",
  "rate": "+0%",
  "style": "cinematic",
  "character": "",
  "aspect_ratio": "9:16",
  "image_provider": "auto",
  "tts_provider": "auto",
  "motion": false,
  "motion_provider": "auto",
  "motion_prompt": "",
  "music_volume": 0.15,
  "openai_model": "gpt-4o-mini",
  "keys": {}
}
```

## Zero-key mode

Images (Pollinations) and voice (gTTS) need no API key. To auto-write the
script, add `OPENAI_API_KEY`. Other providers (Pixabay music, Gemini/HF/Together
images, Replicate/fal.ai motion) are optional and fall back gracefully.

## Where to change things

- **Copy / fields / providers**: `frontend/app/page.tsx` (the `STYLES`,
  `VOICES`, `IMAGE_PROVIDERS`, `KEY_FIELDS` arrays and the form markup).
- **Colors / theme**: `frontend/app/globals.css` (CSS variables) and
  `frontend/tailwind.config.ts`.
- **Pipeline behavior**: `backend/pipeline/modules/` (same as the original
  ProstudioX project).
- **Backend port / CORS**: `backend/main.py`.

## Deploy note (Oracle Cloud)

Run the backend under `systemd` (like the original `prostudiox.service`) and
build the frontend for production:

```bash
cd frontend && npm run build && npm run start   # or `npm run build && npx next start -p 3000`
```

Point `NEXT_PUBLIC_API_URL` at your backend's public URL (or serve both behind
Nginx on the same box).
