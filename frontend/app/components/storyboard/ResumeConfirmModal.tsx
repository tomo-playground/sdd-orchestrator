"use client";

import type { AutoRunStepId } from "../../types";
import { AUTO_RUN_STEPS } from "../../constants";

type ResumeConfirmModalProps = {
  resumeStep: AutoRunStepId;
  timestamp: number;
  onResume: () => void;
  onStartFresh: () => void;
  onDismiss: () => void;
};

function formatRelativeTime(timestamp: number): string {
  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function ResumeConfirmModal({
  resumeStep,
  timestamp,
  onResume,
  onStartFresh,
  onDismiss,
}: ResumeConfirmModalProps) {
  const stepIndex = AUTO_RUN_STEPS.findIndex((s) => s.id === resumeStep);
  const stepLabel = AUTO_RUN_STEPS[stepIndex]?.label || resumeStep;
  const completedSteps = AUTO_RUN_STEPS.slice(0, stepIndex).map((s) => s.label);

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/40 px-6 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-3xl border border-white/60 bg-white/90 p-6 text-sm text-zinc-700 shadow-2xl">
        <div className="mb-4 text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Resume Autopilot
        </div>

        <p className="mb-4 text-base font-semibold text-zinc-900">
          Previous session found
        </p>

        <div className="mb-4 rounded-xl bg-zinc-100 p-4 text-xs">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-zinc-500">Last saved</span>
            <span className="font-medium text-zinc-700">{formatRelativeTime(timestamp)}</span>
          </div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-zinc-500">Resume from</span>
            <span className="font-medium text-zinc-700">{stepLabel}</span>
          </div>
          {completedSteps.length > 0 && (
            <div className="flex items-center justify-between">
              <span className="text-zinc-500">Completed</span>
              <span className="font-medium text-zinc-700">{completedSteps.join(", ")}</span>
            </div>
          )}
        </div>

        <div className="grid gap-2">
          <button
            type="button"
            onClick={onResume}
            className="w-full rounded-full bg-zinc-900 px-4 py-3 text-[10px] font-semibold tracking-[0.2em] text-white uppercase hover:bg-zinc-800"
          >
            Resume from {stepLabel}
          </button>
          <button
            type="button"
            onClick={onStartFresh}
            className="w-full rounded-full border border-zinc-300 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-700 uppercase hover:bg-zinc-50"
          >
            Start Fresh
          </button>
          <button
            type="button"
            onClick={onDismiss}
            className="w-full px-4 py-2 text-[10px] font-medium text-zinc-400 hover:text-zinc-600"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
