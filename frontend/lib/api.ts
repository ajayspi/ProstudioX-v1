const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function apiUrl(path: string): string {
  return `${API}${path}`;
}

export function wsUrl(path: string): string {
  return `${API.replace(/^http/, "ws")}${path}`;
}

export interface GeneratePayload {
  topic: string;
  script?: string;
  voice: string;
  rate: string;
  style: string;
  character: string;
  aspect_ratio: string;
  image_provider: string;
  tts_provider: string;
  motion: boolean;
  motion_provider: string;
  motion_prompt: string;
  music_volume: number;
  openai_model: string;
  keys: Record<string, string>;
}

export async function startGeneration(
  payload: GeneratePayload,
): Promise<{ job_id: string }> {
  const res = await fetch(apiUrl("/api/generate"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Generate failed (${res.status}): ${detail}`);
  }
  return res.json();
}
