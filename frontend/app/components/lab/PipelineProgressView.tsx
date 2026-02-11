"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle,
  Circle,
  Loader2,
  AlertTriangle,
  MessageCircle,
  MinusCircle,
} from "lucide-react";
import type {
  PipelineLog,
  PipelineProgress,
  QCAnalysis,
  ReviewMessage,
  StepProgress,
} from "../../types/creative";
import StepLogs from "./StepLogs";
import StepReviewPanel from "./StepReviewPanel";

type StepReviewData = {
  step: string;
  qc_analysis: QCAnalysis | null;
  messages: ReviewMessage[];
};

type Props = {
  progress: PipelineProgress | null;
  logs: PipelineLog[];
  disabledSteps: string[];
  topic: string;
  review?: StepReviewData | null;
  onReviewAction?: (action: "approve" | "revise", feedback?: string) => void;
};

const STEPS = [
  { key: "scriptwriter", label: "Scriptwriter", desc: "Scene scripts" },
  { key: "cinematographer", label: "Cinematographer", desc: "Visual design" },
  { key: "sound_designer", label: "Sound Designer", desc: "BGM direction" },
  { key: "copyright_reviewer", label: "Copyright", desc: "Originality check" },
] as const;

function resolveStatus(
  value: StepProgress | string | undefined,
  isDisabled: boolean
): string | undefined {
  if (isDisabled) return "skipped";
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
  if (status === "skipped") return <MinusCircle className="h-5 w-5 text-zinc-300" />;
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

function stepCardClass(status: string | undefined): string {
  if (status === "running") return "animate-pulse border-blue-200 bg-blue-50";
  if (status === "done") return "border-emerald-200 bg-emerald-50";
  if (status === "failed") return "border-red-200 bg-red-50";
  if (status === "review") return "border-amber-200 bg-amber-50";
  if (status === "skipped") return "border-zinc-100 bg-zinc-50 opacity-50";
  return "border-zinc-100 bg-zinc-50";
}

function statusBadgeClass(status: string): string {
  if (status === "done") return "bg-emerald-100 text-emerald-700";
  if (status === "running") return "bg-blue-100 text-blue-700";
  if (status === "failed") return "bg-red-100 text-red-700";
  if (status === "review") return "bg-amber-100 text-amber-700";
  if (status === "skipped") return "bg-zinc-100 text-zinc-400";
  return "bg-zinc-100 text-zinc-500";
}

export default function PipelineProgressView({
  progress,
  logs,
  disabledSteps,
  topic,
  review,
  onReviewAction,
}: Props) {
  const p = progress ?? {};
  const disabledSet = new Set(disabledSteps);

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
          const status = resolveStatus(raw, disabledSet.has(step.key));
          const retryCount = resolveRetry(raw);
          const isActive = status === "running";

          return (
            <div
              key={step.key}
              className={`rounded-lg border p-3 transition ${stepCardClass(status)}`}
            >
              <div className="flex items-center gap-3">
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
                    className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${statusBadgeClass(status)}`}
                  >
                    {status}
                  </span>
                )}
              </div>

              <StepLogs logs={logs} stepKey={step.key} isRunning={isActive} />

              {status === "review" && review?.step === step.key && (
                <StepReviewPanel review={review} onAction={onReviewAction} />
              )}
            </div>
          );
        })}
      </div>

      <p className="text-center text-[10px] text-zinc-400">Pipeline running in background...</p>
    </div>
  );
}
