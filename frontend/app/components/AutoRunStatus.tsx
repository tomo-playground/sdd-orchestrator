"use client";

import type { AutoRunState } from "../types";
import { AUTO_RUN_STEPS } from "../constants";

type AutoRunStatusProps = {
  autoRunState: AutoRunState;
  autoRunLog: string[];
  onResume: () => void;
  onRestart: () => void;
};

export default function AutoRunStatus({
  autoRunState,
  autoRunLog,
  onResume,
  onRestart,
}: AutoRunStatusProps) {
  if (autoRunState.status === "idle") {
    return null;
  }

  return (
    <div className="grid gap-3 rounded-2xl border border-zinc-200 bg-white/80 p-4 text-xs text-zinc-600">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Autopilot Status
        </span>
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
          return (
            <span
              key={step.id}
              className={`rounded-full px-3 py-1 text-[10px] font-semibold tracking-[0.2em] uppercase ${
                isActive
                  ? "bg-zinc-900 text-white"
                  : isDone
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-zinc-100 text-zinc-500"
              }`}
            >
              {step.label}
            </span>
          );
        })}
      </div>
      <p>{autoRunState.message}</p>
      {autoRunState.error && <p className="text-red-500">{autoRunState.error}</p>}
      {autoRunState.status === "error" && autoRunState.step !== "idle" && (
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onResume}
            className="rounded-full bg-zinc-900 px-4 py-1.5 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-sm transition hover:bg-zinc-800"
          >
            Resume from Step
          </button>
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
