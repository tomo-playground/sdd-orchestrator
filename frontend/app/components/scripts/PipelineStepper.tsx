"use client";

import { Check, AlertCircle } from "lucide-react";
import type { PipelineStep } from "../../types";

type Props = {
  steps: PipelineStep[];
  currentNode?: string;
  percent?: number;
  onStepClick?: (stepId: string) => void;
};

function stepIcon(status: PipelineStep["status"]) {
  switch (status) {
    case "done":
      return <Check className="h-3.5 w-3.5 text-white" />;
    case "error":
      return <AlertCircle className="h-3.5 w-3.5 text-white" />;
    default:
      return null;
  }
}

function dotClasses(status: PipelineStep["status"]): string {
  const base =
    "flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium transition-all";
  switch (status) {
    case "done":
      return `${base} bg-emerald-500`;
    case "running":
      return `${base} bg-amber-400 animate-pulse`;
    case "error":
      return `${base} bg-red-500`;
    default:
      return `${base} bg-zinc-300`;
  }
}

function lineColor(status: PipelineStep["status"]): string {
  if (status === "done") return "bg-emerald-400";
  if (status === "running") return "bg-amber-300";
  return "bg-zinc-200";
}

export default function PipelineStepper({ steps, percent, onStepClick }: Props) {
  if (steps.length === 0) return null;

  return (
    <div className="mt-4 space-y-3">
      {/* Stepper */}
      <div className="flex items-center overflow-x-auto pb-1">
        {steps.map((step, i) => (
          <div key={step.id} className="flex items-center">
            {/* Step dot + label */}
            <button
              type="button"
              className="group relative flex flex-col items-center gap-1"
              onClick={() => onStepClick?.(step.id)}
              disabled={!onStepClick}
              title={step.nodes?.join(", ")}
            >
              <div className={dotClasses(step.status)}>
                {stepIcon(step.status) ?? <span className="text-xs text-white">{i + 1}</span>}
              </div>
              <span
                className={`text-xs whitespace-nowrap ${
                  step.status === "running"
                    ? "font-semibold text-amber-700"
                    : step.status === "done"
                      ? "text-emerald-700"
                      : step.status === "error"
                        ? "text-red-600"
                        : "text-zinc-400"
                }`}
              >
                {step.label}
              </span>
              {/* Agent nodes tooltip */}
              {step.nodes && step.nodes.length > 0 && (
                <div className="pointer-events-none absolute -bottom-9 left-1/2 z-10 hidden -translate-x-1/2 rounded bg-zinc-800 px-2.5 py-1 text-xs whitespace-nowrap text-zinc-200 shadow-lg group-hover:block">
                  {step.nodes.join(" → ")}
                </div>
              )}
            </button>
            {/* Connector line */}
            {i < steps.length - 1 && (
              <div className={`mx-1.5 h-0.5 w-7 rounded-full ${lineColor(step.status)}`} />
            )}
          </div>
        ))}
      </div>
      {/* Percent bar (보조) */}
      {percent != null && percent > 0 && (
        <div className="h-1 overflow-hidden rounded-full bg-zinc-100">
          <div
            className="h-full rounded-full bg-zinc-900 transition-all duration-500"
            style={{ width: `${percent}%` }}
          />
        </div>
      )}
    </div>
  );
}
