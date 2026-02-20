"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import Button from "../../../../components/ui/Button";

type WizardNavBarProps = {
  step: number;
  totalSteps: number;
  onBack: () => void;
  onNext: () => void;
  isSaving: boolean;
  isLastStep: boolean;
  canProceed: boolean;
  onSkipToEnd?: () => void;
};

export default function WizardNavBar({
  step,
  totalSteps,
  onBack,
  onNext,
  isSaving,
  isLastStep,
  canProceed,
  onSkipToEnd,
}: WizardNavBarProps) {
  return (
    <div className="sticky bottom-0 z-10 border-t border-zinc-200 bg-white/95 px-6 py-3 backdrop-blur-sm">
      <div className="flex items-center justify-between">
        {/* Step indicator */}
        <div className="flex items-center gap-2">
          {Array.from({ length: totalSteps }, (_, i) => (
            <div
              key={i}
              className={`h-1.5 w-6 rounded-full transition-colors ${
                i + 1 <= step ? "bg-zinc-900" : "bg-zinc-200"
              }`}
            />
          ))}
          <span className="ml-2 text-xs text-zinc-400">
            Step {step} of {totalSteps}
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {step > 1 && (
            <Button variant="ghost" size="sm" onClick={onBack}>
              <ArrowLeft className="h-3.5 w-3.5" />
              Back
            </Button>
          )}
          {onSkipToEnd && !isLastStep && step === totalSteps - 1 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onSkipToEnd}
              loading={isSaving}
              disabled={!canProceed}
            >
              Create Character
            </Button>
          )}
          <Button size="sm" onClick={onNext} loading={isSaving} disabled={!canProceed}>
            {isSaving ? (
              "Creating..."
            ) : isLastStep ? (
              "Create Character"
            ) : (
              <>
                Next
                <ArrowRight className="h-3.5 w-3.5" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
