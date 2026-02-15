"use client";

import { Check } from "lucide-react";

type Props = {
  currentStep: 1 | 2;
  completedSteps: number[];
};

const STEPS = [
  { step: 1, label: "채널" },
  { step: 2, label: "시리즈" },
] as const;

export default function SetupWizardStepIndicator({ currentStep, completedSteps }: Props) {
  return (
    <div className="flex items-center justify-center gap-3 py-4">
      {STEPS.map(({ step, label }, idx) => {
        const isCompleted = completedSteps.includes(step);
        const isCurrent = currentStep === step;

        return (
          <div key={step} className="flex items-center gap-3">
            {idx > 0 && (
              <div
                className={`h-px w-10 ${isCompleted || isCurrent ? "bg-zinc-900" : "bg-zinc-200"}`}
              />
            )}
            <div className="flex items-center gap-1.5">
              <div
                className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                  isCompleted
                    ? "bg-zinc-900 text-white"
                    : isCurrent
                      ? "bg-zinc-900 font-semibold text-white"
                      : "border-2 border-zinc-300 bg-white text-zinc-400"
                }`}
              >
                {isCompleted ? <Check className="h-3.5 w-3.5" /> : step}
              </div>
              <span
                className={`text-xs ${isCurrent || isCompleted ? "font-semibold text-zinc-900" : "text-zinc-400"}`}
              >
                {label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
