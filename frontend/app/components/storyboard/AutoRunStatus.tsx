"use client";

import type { AutoRunState, AutoRunStepId } from "../../types";
import { AUTO_RUN_STEPS } from "../../constants";

type AutoRunStatusProps = {
  autoRunState: AutoRunState;
  autoRunLog: string[];
  storyboardTitle?: string;
  onResume: (step: AutoRunStepId) => void;
  onRestart: () => void;
};

export default function AutoRunStatus({
  autoRunState,
  autoRunLog,
  storyboardTitle,
  onResume,
  onRestart,
}: AutoRunStatusProps) {
  if (autoRunState.status === "idle") {
    return null;
  }

  return (
    <div className="grid gap-3 rounded-2xl border border-zinc-200 bg-white/80 p-4 text-xs text-zinc-600">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Autopilot
          </span>
          {storyboardTitle && (
            <span className="max-w-[200px] truncate rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-medium text-zinc-600">
              {storyboardTitle}
            </span>
          )}
        </div>
        <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          {autoRunState.status}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {AUTO_RUN_STEPS.map((step) => {
          const isActive = autoRunState.step === step.id;
          const isDone =
            autoRunState.status !== "idle" &&
            AUTO_RUN_STEPS.findIndex((item) => item.id === step.id) <
              AUTO_RUN_STEPS.findIndex((item) => item.id === autoRunState.step);
          const isError = autoRunState.status === "error";
          const baseClass = `rounded-full px-3 py-1 text-[10px] font-semibold tracking-[0.2em] uppercase ${
            isActive
              ? "bg-zinc-900 text-white"
              : isDone
                ? "bg-emerald-100 text-emerald-700"
                : "bg-zinc-100 text-zinc-500"
          }`;
          if (isError) {
            return (
              <button
                key={step.id}
                type="button"
                onClick={() => onResume(step.id as AutoRunStepId)}
                className={`${baseClass} cursor-pointer transition hover:ring-2 hover:ring-zinc-400`}
              >
                {step.label}
              </button>
            );
          }
          return (
            <span key={step.id} className={baseClass}>
              {step.label}
            </span>
          );
        })}
      </div>
      <p>{autoRunState.message}</p>
      {autoRunState.error && <p className="text-red-500">{autoRunState.error}</p>}
      {autoRunState.status === "error" && autoRunState.step !== "idle" && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] text-zinc-400">Click a step to resume from</span>
          <button
            type="button"
            onClick={onRestart}
            className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 text-[10px] font-medium tracking-[0.15em] text-zinc-500 uppercase transition hover:border-zinc-400 hover:text-zinc-600"
          >
            Restart
          </button>
        </div>
      )}
      {autoRunLog.length > 0 && (
        <div className="grid gap-1 text-[11px] text-zinc-500">
          {autoRunLog.map((entry, idx) => (
            <span key={`${entry}-${idx}`}>• {entry}</span>
          ))}
        </div>
      )}
    </div>
  );
}
