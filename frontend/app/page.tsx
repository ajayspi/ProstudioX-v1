"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Clapperboard, KeyRound, Loader2, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  IdleHint,
  PipelineProgress,
  type JobStatus,
} from "@/components/pipeline-progress";
import { startGeneration, wsUrl } from "@/lib/api";

const STYLES = [
  "cinematic",
  "photographic",
  "minimal",
  "dark",
  "documentary",
  "3d render",
  "flat illustration",
  "isometric",
  "retro",
  "neon",
];
const VOICES = [
  "en-US-GuyNeural",
  "en-US-AriaNeural",
  "en-US-JennyNeural",
  "en-US-ChristopherNeural",
  "en-GB-RyanNeural",
  "en-GB-SoniaNeural",
  "en-AU-NatashaNeural",
];
const ASPECTS = ["9:16", "16:9", "1:1", "4:5"];
const IMAGE_PROVIDERS = ["auto", "pollinations", "huggingface", "together", "gemini", "openai"];
const TTS_PROVIDERS = ["auto", "edge", "gtts", "openai"];
const MOTION_PROVIDERS = ["auto", "replicate", "fal"];
const RATES = ["+0%", "+5%", "+10%", "-5%", "-10%"];

const KEY_FIELDS: { id: string; env: string; label: string }[] = [
  { id: "openai", env: "OPENAI_API_KEY", label: "OpenAI (auto script)" },
  { id: "pixabay", env: "PIXABAY_API_KEY", label: "Pixabay (music)" },
  { id: "gemini", env: "GEMINI_API_KEY", label: "Gemini (images)" },
  { id: "hf", env: "HF_TOKEN", label: "Hugging Face (FLUX)" },
  { id: "together", env: "TOGETHER_API_KEY", label: "Together (FLUX)" },
  { id: "replicate", env: "REPLICATE_API_TOKEN", label: "Replicate (motion)" },
  { id: "fal", env: "FAL_KEY", label: "fal.ai (motion)" },
];

interface FormState {
  topic: string;
  script: string;
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
  use_supabase: boolean;
}

const DEFAULTS: FormState = {
  topic: "",
  script: "",
  voice: "en-US-GuyNeural",
  rate: "+0%",
  style: "cinematic",
  character: "",
  aspect_ratio: "9:16",
  image_provider: "auto",
  tts_provider: "auto",
  motion: false,
  motion_provider: "auto",
  motion_prompt: "",
  music_volume: 0.15,
  openai_model: "gpt-4o-mini",
  use_supabase: false,
};

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h2>
      {children}
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export default function Page() {
  const [form, setForm] = useState<FormState>(DEFAULTS);
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [showKeys, setShowKeys] = useState(false);

  const [status, setStatus] = useState<JobStatus>("idle");
  const [step, setStep] = useState("");
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState("");
  const [elapsed, setElapsed] = useState(0);

  const update = (patch: Partial<FormState>) =>
    setForm((f) => ({ ...f, ...patch }));

  useEffect(() => {
    if (status !== "running") return;
    const id = setInterval(() => setElapsed((e) => e + 0.5), 500);
    return () => clearInterval(id);
  }, [status]);

  const busy = status === "running";

  function buildKeys(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const f of KEY_FIELDS) {
      const v = keys[f.id];
      if (v && v.trim()) out[f.env] = v.trim();
    }
    return out;
  }

  async function handleGenerate() {
    if (!form.topic.trim()) {
      setError("Enter a topic first.");
      return;
    }
    setStatus("running");
    setStep("starting");
    setError("");
    setElapsed(0);
    setJobId("");
    try {
      const { job_id } = await startGeneration({
        ...form,
        topic: form.topic.trim(),
        keys: buildKeys(),
      });
      setJobId(job_id);

      const ws = new WebSocket(wsUrl(`/ws/${job_id}`));
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === "snapshot") {
            setStep(data.step ?? "");
            setStatus(mapStatus(data.status));
            if (data.status === "failed") setError(data.error ?? "Generation failed");
          } else if (data.type === "step") {
            setStep(data.step ?? "");
          } else if (data.type === "status") {
            setStep(data.step ?? "");
            const s = mapStatus(data.status);
            setStatus(s);
            if (s === "failed") setError(data.error ?? "Generation failed");
          } else if (data.type === "progress" && data.status === "failed") {
            setError(data.error ?? "Generation failed");
          } else if (data.type === "end") {
            setStatus(mapStatus(data.status));
            ws.close();
          }
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onerror = () => {
        setError("Lost connection to the backend — is it running on port 8000?");
      };
    } catch (e) {
      setStatus("failed");
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-6xl px-4 py-8 md:px-6">
        <header className="mb-8 flex flex-wrap items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/30">
            <Clapperboard className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              Prostudio <span className="text-primary">v1</span>
            </h1>
            <p className="text-sm text-muted-foreground">
              Faceless finance Shorts — turn a topic into a finished video.
            </p>
          </div>
          <Badge variant="outline" className="ml-auto">
            FastAPI · Next.js · Framer Motion
          </Badge>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_380px]">
          {/* Left — settings */}
          <Card>
            <CardHeader>
              <CardTitle>Create a Short</CardTitle>
              <CardDescription>
                Everything in one place. Images (Pollinations) and voice (gTTS)
                work with no API key.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <Section title="Content">
                <Field
                  label="Topic"
                  hint="e.g. “3 money habits that quietly make you richer”"
                >
                  <Textarea
                    value={form.topic}
                    onChange={(e) => update({ topic: e.target.value })}
                    placeholder="Your topic…"
                    rows={2}
                  />
                </Field>
                <Field
                  label="Script (optional)"
                  hint="Leave blank to auto-write with OpenAI; paste your own to skip the LLM."
                >
                  <Textarea
                    value={form.script}
                    onChange={(e) => update({ script: e.target.value })}
                    placeholder="Paste a script to override the auto-writer…"
                    rows={3}
                  />
                </Field>
              </Section>

              <Separator />

              <Section title="Voice">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <Field label="Voice">
                    <Select
                      value={form.voice}
                      onChange={(e) => update({ voice: e.target.value })}
                    >
                      {VOICES.map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Rate">
                    <Select
                      value={form.rate}
                      onChange={(e) => update({ rate: e.target.value })}
                    >
                      {RATES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="TTS provider">
                    <Select
                      value={form.tts_provider}
                      onChange={(e) => update({ tts_provider: e.target.value })}
                    >
                      {TTS_PROVIDERS.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
              </Section>

              <Separator />

              <Section title="Visuals">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <Field label="Style preset">
                    <Select
                      value={form.style}
                      onChange={(e) => update({ style: e.target.value })}
                    >
                      {STYLES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Aspect ratio">
                    <Select
                      value={form.aspect_ratio}
                      onChange={(e) => update({ aspect_ratio: e.target.value })}
                    >
                      {ASPECTS.map((a) => (
                        <option key={a} value={a}>
                          {a}
                        </option>
                      ))}
                    </Select>
                  </Field>
                  <Field label="Image provider">
                    <Select
                      value={form.image_provider}
                      onChange={(e) => update({ image_provider: e.target.value })}
                    >
                      {IMAGE_PROVIDERS.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </Select>
                  </Field>
                </div>
                <Field
                  label="Consistent character (optional)"
                  hint="Prepended to every image, e.g. “a 30-year-old woman in a blazer”."
                >
                  <Input
                    value={form.character}
                    onChange={(e) => update({ character: e.target.value })}
                    placeholder="Leave empty for pure B-roll"
                  />
                </Field>
              </Section>

              <Separator />

              <Section title="Motion (optional)">
                <div className="flex items-center justify-between rounded-md border p-3">
                  <div className="space-y-0.5">
                    <Label>Animate images</Label>
                    <p className="text-xs text-muted-foreground">
                      Image-to-video via Replicate/fal.ai — needs a key.
                    </p>
                  </div>
                  <Switch
                    checked={form.motion}
                    onCheckedChange={(v) => update({ motion: v })}
                  />
                </div>
                {form.motion && (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <Field label="Motion provider">
                      <Select
                        value={form.motion_provider}
                        onChange={(e) =>
                          update({ motion_provider: e.target.value })
                        }
                      >
                        {MOTION_PROVIDERS.map((p) => (
                          <option key={p} value={p}>
                            {p}
                          </option>
                        ))}
                      </Select>
                    </Field>
                    <Field label="Motion prompt">
                      <Input
                        value={form.motion_prompt}
                        onChange={(e) => update({ motion_prompt: e.target.value })}
                        placeholder="e.g. slow zoom in"
                      />
                    </Field>
                  </div>
                )}
              </Section>

              <Separator />

              <Section title="Storage">
                <div className="flex items-center justify-between rounded-md border p-3">
                  <div className="space-y-0.5">
                    <Label>Save to Supabase</Label>
                    <p className="text-xs text-muted-foreground">
                      Upload the finished video and record it in your Supabase project.
                    </p>
                  </div>
                  <Switch
                    checked={form.use_supabase}
                    onCheckedChange={(v) => update({ use_supabase: v })}
                  />
                </div>
              </Section>

              <Separator />

              <Section title="Audio & model">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Field label={`Music volume — ${(form.music_volume * 100).toFixed(0)}%`}>
                    <Slider
                      min={0}
                      max={1}
                      step={0.05}
                      value={form.music_volume}
                      onChange={(e) =>
                        update({ music_volume: Number(e.target.value) })
                      }
                    />
                  </Field>
                  <Field label="Script LLM">
                    <Input
                      value={form.openai_model}
                      onChange={(e) => update({ openai_model: e.target.value })}
                    />
                  </Field>
                </div>
              </Section>

              <Separator />

              <div>
                <button
                  type="button"
                  onClick={() => setShowKeys((s) => !s)}
                  className="flex items-center gap-2 text-sm font-medium text-primary hover:underline"
                >
                  <KeyRound className="h-4 w-4" />
                  API keys {showKeys ? "▲" : "▼"}
                </button>
                <AnimatePresence>
                  {showKeys && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="grid grid-cols-1 gap-3 pt-3 sm:grid-cols-2">
                        {KEY_FIELDS.map((f) => (
                          <Field key={f.id} label={f.label}>
                            <Input
                              type="password"
                              value={keys[f.id] ?? ""}
                              onChange={(e) =>
                                setKeys((k) => ({ ...k, [f.id]: e.target.value }))
                              }
                              placeholder="Optional"
                              autoComplete="off"
                            />
                          </Field>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {error && !busy && (
                <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <Button
                size="lg"
                className="w-full"
                onClick={handleGenerate}
                disabled={busy}
              >
                {busy ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Generating…
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" /> Generate Short
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Right — pipeline */}
          <div className="space-y-6">
            {status === "idle" ? (
              <IdleHint />
            ) : (
              <PipelineProgress
                status={status}
                step={step}
                error={error}
                jobId={jobId}
                elapsed={elapsed}
              />
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

function mapStatus(s: string): JobStatus {
  if (s === "done") return "done";
  if (s === "failed") return "failed";
  if (s === "running" || s === "generating") return "running";
  return "idle";
}
