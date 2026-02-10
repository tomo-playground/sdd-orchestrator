"use client";

import { useEffect, useState } from "react";
import { CheckCircle, Circle, Loader2, AlertTriangle, MessageCircle } from "lucide-react";
import type { PipelineProgress, StepProgress } from "../../types/creative";

type Props = {
  progress: PipelineProgress | null;
  topic: string;
};

const STEPS = [
  { key: "scriptwriter", label: "Scriptwriter", desc: "Scene scripts" },
  { key: "cinematographer", label: "Cinematographer", desc: "Visual design" },
  { key: "sound_designer", label: "Sound Designer", desc: "BGM direction" },
  { key: "copyright_reviewer", label: "Copyright", desc: "Originality check" },
] as const;

function resolveStatus(value: StepProgress | string | undefined): string | undefined {
  if (!value) return undefined;
  if (typeof value === "string") return value;
  return value.status;
}

function resolveRetry(value: StepProgress | string | undefined): number {
  if (!value || typeof value === "string") return 0;
  return value.retry_count ?? 0;
}

function StepIcon({ status }: { status: string | undefined }) {
  if (status === "done") return <CheckCircle className="h-5 w-5 text-emerald-500" />;
  if (status === "running") return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
  if (status === "failed") return <AlertTriangle className="h-5 w-5 text-red-500" />;
  if (status === "review") return <MessageCircle className="h-5 w-5 text-amber-500" />;
  return <Circle className="h-5 w-5 text-zinc-300" />;
}

function ElapsedTicker() {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => setElapsed((p) => p + 1), 1000);
    return () => clearInterval(interval);
  }, []);
  return <span className="text-[10px] text-blue-500">{elapsed}s</span>;
}

export default function PipelineProgressView({ progress, topic }: Props) {
  const p = progress ?? {};

  return (
    <div className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5">
      <div>
        <p className="text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
          Phase 2: Production Pipeline
        </p>
        <p className="mt-1 text-xs text-zinc-600">{topic}</p>
      </div>

      <div className="space-y-3">
        {STEPS.map((step) => {
          const raw = p[step.key as keyof PipelineProgress];
          const status = resolveStatus(raw);
          const retryCount = resolveRetry(raw);
          const isActive = status === "running";
          return (
            <div
              key={step.key}
              className={`flex items-center gap-3 rounded-lg border p-3 transition ${
                isActive
                  ? "animate-pulse border-blue-200 bg-blue-50"
                  : status === "done"
                    ? "border-emerald-200 bg-emerald-50"
                    : status === "failed"
                      ? "border-red-200 bg-red-50"
                      : status === "review"
                        ? "border-amber-200 bg-amber-50"
                        : "border-zinc-100 bg-zinc-50"
              }`}
            >
              <StepIcon status={status} />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-xs font-semibold text-zinc-700">{step.label}</p>
                  {isActive && <ElapsedTicker />}
                </div>
                <p className="text-[10px] text-zinc-400">
                  {step.desc}
                  {retryCount > 0 && (
                    <span className="ml-1 text-amber-500">(retry {retryCount})</span>
                  )}
                </p>
              </div>
              {status && (
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                    status === "done"
                      ? "bg-emerald-100 text-emerald-700"
                      : status === "running"
                        ? "bg-blue-100 text-blue-700"
                        : status === "failed"
                          ? "bg-red-100 text-red-700"
                          : status === "review"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-zinc-100 text-zinc-500"
                  }`}
                >
                  {status}
                </span>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-center text-[10px] text-zinc-400">Pipeline running in background...</p>
    </div>
  );
}
