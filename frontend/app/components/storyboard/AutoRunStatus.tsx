"use client";

import { useEffect, useRef, useState } from "react";
import type { AutoRunState, AutoRunStepId } from "../../types";
import { AUTO_RUN_STEPS } from "../../constants";

type AutoRunStatusProps = {
  autoRunState: AutoRunState;
  autoRunLog: string[];
  autoRunProgress?: number;
  storyboardTitle?: string;
  onResume: (step: AutoRunStepId) => void;
  onRestart: () => void;
  onCancel?: () => void;
};

export default function AutoRunStatus({
  autoRunState,
  autoRunLog,
  autoRunProgress,
  storyboardTitle,
  onResume,
  onRestart,
  onCancel,
}: AutoRunStatusProps) {
  const [isLogCollapsed, setIsLogCollapsed] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [autoRunLog.length]);

  if (autoRunState.status === "idle") {
    return null;
  }

  const isError = autoRunState.status === "error";

  return (
    <div className="grid gap-3 rounded-2xl border border-zinc-200 bg-white/80 p-4 text-xs text-zinc-600">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Autopilot
          </span>
          {storyboardTitle && (
            <span className="max-w-[200px] truncate rounded-full bg-zinc-100 px-2 py-0.5 text-[12px] font-medium text-zinc-600">
              {storyboardTitle}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            {autoRunState.status}
          </span>
          {autoRunState.status === "running" && onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="rounded-full border border-red-200 bg-red-50 px-3 py-0.5 text-[12px] font-semibold text-red-600 transition hover:border-red-300 hover:bg-red-100"
            >
              Stop
            </button>
          )}
          {autoRunLog.length > 0 && (
            <button
              type="button"
              onClick={() => setIsLogCollapsed((v) => !v)}
              className="rounded-md px-1.5 py-0.5 text-[11px] text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-600"
              title={isLogCollapsed ? "Show log" : "Hide log"}
            >
              {isLogCollapsed ? "▶ Log" : "▼ Log"}
            </button>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {AUTO_RUN_STEPS.map((step) => {
          const isActive = autoRunState.step === step.id;
          const isDone =
            autoRunState.status !== "idle" &&
            AUTO_RUN_STEPS.findIndex((item) => item.id === step.id) <
              AUTO_RUN_STEPS.findIndex((item) => item.id === autoRunState.step);
          const baseClass = `rounded-full px-3 py-1 text-[12px] font-semibold tracking-[0.2em] uppercase ${
            isActive
              ? "bg-zinc-900 text-white"
              : isDone
                ? "bg-emerald-100 text-emerald-700"
                : "bg-zinc-100 text-zinc-500"
          }`;
          if (isError) {
            if (isDone) {
              // 완료된 단계는 error 상태에서도 클릭 불가
              return (
                <span key={step.id} className={baseClass}>
                  {step.label}
                </span>
              );
            }
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
      {autoRunState.status === "running" && autoRunProgress != null && (
        <div className="h-1 w-full overflow-hidden rounded-full bg-zinc-100">
          <div
            className="h-full rounded-full bg-zinc-800 transition-all duration-500"
            style={{ width: `${autoRunProgress}%` }}
          />
        </div>
      )}
      <p>{autoRunState.message}</p>
      {autoRunState.error && <p className="text-red-500">{autoRunState.error}</p>}
      {isError && autoRunState.step !== "idle" && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[12px] text-zinc-400">Click a step to resume from</span>
          <button
            type="button"
            onClick={onRestart}
            className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 text-[12px] font-medium tracking-[0.15em] text-zinc-500 uppercase transition hover:border-zinc-400 hover:text-zinc-600"
          >
            Restart
          </button>
        </div>
      )}
      {autoRunLog.length > 0 && !isLogCollapsed && (
        <div className="max-h-32 overflow-y-auto rounded-lg bg-zinc-50 p-2">
          <div className="grid gap-1 text-[13px] text-zinc-500">
            {autoRunLog.map((entry, idx) => (
              <span key={`${entry}-${idx}`}>• {entry}</span>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      )}
    </div>
  );
}
