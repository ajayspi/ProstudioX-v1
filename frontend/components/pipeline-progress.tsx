"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check, Download, Film } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { apiUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

export type JobStatus = "idle" | "running" | "done" | "failed";

const STEPS = [
  { id: "script", label: "Script" },
  { id: "voice", label: "Voiceover" },
  { id: "images", label: "Images" },
  { id: "music", label: "Music" },
  { id: "render", label: "Render" },
  { id: "done", label: "Done" },
];

function stepIndex(step: string): number {
  const i = STEPS.findIndex((s) => s.id === step);
  return i === -1 ? -1 : i;
}

type StepState = "done" | "active" | "pending";

function Step({
  label,
  state,
  index,
}: {
  label: string;
  state: StepState;
  index: number;
}) {
  return (
    <li className="flex items-center gap-2">
      <motion.span
        animate={state === "active" ? { scale: [1, 1.15, 1] } : { scale: 1 }}
        transition={
          state === "active"
            ? { repeat: Infinity, duration: 1.2, ease: "easeInOut" }
            : { duration: 0.2 }
        }
        className={cn(
          "flex h-7 w-7 items-center justify-center rounded-full border text-xs font-semibold transition-colors",
          state === "done" && "border-success bg-success/15 text-success",
          state === "active" &&
            "border-primary bg-primary text-primary-foreground",
          state === "pending" &&
            "border-border bg-muted text-muted-foreground",
        )}
      >
        {state === "done" ? <Check className="h-3.5 w-3.5" /> : index + 1}
      </motion.span>
      <span
        className={cn(
          "text-xs",
          state === "active"
            ? "font-medium text-foreground"
            : "text-muted-foreground",
        )}
      >
        {label}
      </span>
    </li>
  );
}

function StatusBadge({ status }: { status: JobStatus }) {
  if (status === "running")
    return <Badge variant="secondary">Generating…</Badge>;
  if (status === "done") return <Badge variant="success">Done</Badge>;
  if (status === "failed") return <Badge variant="destructive">Failed</Badge>;
  return null;
}

export function PipelineProgress({
  status,
  step,
  error,
  jobId,
  elapsed,
}: {
  status: JobStatus;
  step: string;
  error: string;
  jobId: string;
  elapsed: number;
}) {
  if (status === "idle") return null;

  const active = stepIndex(step);
  const progressPct =
    status === "done" || status === "failed"
      ? 100
      : Math.max(6, ((active + 1) / STEPS.length) * 100);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="border-primary/20">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle>Pipeline</CardTitle>
                <CardDescription>Live generation progress</CardDescription>
              </div>
              <StatusBadge status={status} />
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <ol className="flex flex-wrap items-center gap-x-4 gap-y-3">
              {STEPS.map((s, i) => {
                const state: StepState =
                  status === "failed" && i > active
                    ? "pending"
                    : i < active
                      ? "done"
                      : i === active
                        ? "active"
                        : "pending";
                return (
                  <Step key={s.id} label={s.label} state={state} index={i} />
                );
              })}
            </ol>

            <Progress value={progressPct} />

            {status === "running" && (
              <p className="text-sm text-muted-foreground">
                Working on{" "}
                <span className="font-medium capitalize text-foreground">
                  {step || "…"}
                </span>
                …{" "}
                {elapsed > 0 && (
                  <span className="tabular-nums">({elapsed.toFixed(0)}s)</span>
                )}
              </p>
            )}

            {status === "failed" && error && (
              <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                <span className="font-semibold">Failed:</span> {error}
              </div>
            )}

            {status === "done" && (
              <div className="space-y-3">
                <Separator />
                <div className="flex items-center gap-2 text-sm text-success">
                  <Check className="h-4 w-4" /> Video ready
                </div>
                <video
                  src={apiUrl(`/api/jobs/${jobId}/video`)}
                  controls
                  playsInline
                  className="aspect-[9/16] w-full max-w-[260px] rounded-lg border bg-black"
                />
                <a
                  href={apiUrl(`/api/jobs/${jobId}/video`)}
                  download
                  className={cn(buttonVariants({ size: "sm" }), "w-full")}
                >
                  <Download className="h-4 w-4" /> Download MP4
                </a>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}

export function IdleHint() {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center gap-2 py-10 text-center">
        <Film className="h-6 w-6 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Your generation pipeline will appear here.
        </p>
      </CardContent>
    </Card>
  );
}
