#!/usr/bin/env python3
"""
ProstudioX — headless generator CLI.

Turns topics into finished finance Shorts without the Streamlit UI.

Examples:
    # One topic (script auto-generated via OpenAI)
    python generate.py --topic "3 money habits that quietly make you richer"

    # Several topics from a file (one per line)
    python generate.py --topics topics.txt

    # Skip the LLM and supply the script directly
    python generate.py --topic "The 50/30/20 rule" --script "Hook. Point one. Point two. Point three. Call to action."

    # Also upload to Supabase (requires SUPABASE_URL + SERVICE_ROLE_KEY)
    python generate.py --topic "..." --use-supabase
"""

import argparse
import sys

from modules.batch_manager import BatchProcessor


def main():
    p = argparse.ArgumentParser(description="ProstudioX headless video generator")
    p.add_argument("--topic", help="single topic")
    p.add_argument("--topics", help="path to a text file with one topic per line")
    p.add_argument("--script", default="", help="supply the script directly (skip LLM)")
    p.add_argument("--voice", default="en-US-GuyNeural",
                   help="edge-tts voice (e.g. en-US-GuyNeural, en-US-AriaNeural)")
    p.add_argument("--rate", default="+0%", help="speech rate, e.g. +5%")
    p.add_argument("--out", default="outputs", help="output root dir")
    p.add_argument("--music-volume", type=float, default=0.15,
                   help="background music volume under voiceover")
    p.add_argument("--image-provider", default="auto",
                   help="image provider: gemini | pollinations | openai | auto")
    p.add_argument("--tts-provider", default="auto",
                   help="TTS provider: edge | gtts | openai | auto")
    p.add_argument("--style", default="cinematic",
                   help="visual style preset: cinematic | photographic | minimal | dark | 3d render | flat illustration | ...")
    p.add_argument("--character", default="",
                   help="consistent character description prepended to every image (empty = pure B-roll)")
    p.add_argument("--aspect-ratio", default="9:16",
                   help="output aspect ratio: 9:16 | 16:9 | 1:1 | 4:5")
    p.add_argument("--motion", action="store_true",
                   help="animate each image into a motion clip (image-to-video)")
    p.add_argument("--motion-provider", default="auto",
                   help="motion provider: replicate | fal | auto")
    p.add_argument("--motion-prompt", default="",
                   help="optional motion prompt, e.g. 'slow zoom in'")
    p.add_argument("--use-supabase", action="store_true",
                   help="upload + record in Supabase after generation")
    args = p.parse_args()

    topics = []
    if args.topics:
        with open(args.topics, encoding="utf-8") as f:
            topics = [ln.strip() for ln in f if ln.strip()]
    elif args.topic:
        topics = [args.topic]

    if not topics:
        print("No topics. Use --topic or --topics.")
        sys.exit(1)

    bp = BatchProcessor(
        voice=args.voice, rate=args.rate, out_root=args.out,
        music_volume=args.music_volume, use_supabase=args.use_supabase,
        image_provider=args.image_provider, tts_provider=args.tts_provider,
        style=args.style, character=args.character, aspect_ratio=args.aspect_ratio,
        motion=args.motion, motion_provider=args.motion_provider,
        motion_prompt=args.motion_prompt,
    )

    for t in topics:
        bp.add_video(t, script=args.script)

    def progress(job):
        tail = f" -> {job.output_path}" if job.output_path else ""
        if job.status == "failed":
            tail += f" (error: {job.error})"
        print(f"[{job.status:11s}] {job.topic[:48]}  {job.elapsed}s{tail}")

    result = bp.process(on_progress=progress)

    print(f"\nDone: {result.done}  Failed: {result.failed}")
    for j in result.jobs:
        if j.status == "done":
            extra = f"  |  {j.public_url}" if j.public_url else ""
            print(f"  OK   {j.topic} -> {j.output_path}{extra}")
        else:
            print(f"  FAIL {j.topic} -> {j.error}")


if __name__ == "__main__":
    main()
