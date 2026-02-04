"use client";

import type { AutoRunStepId } from "../../types";
import { AUTO_RUN_STEPS } from "../../constants";
import LoadingSpinner from "../ui/LoadingSpinner";

type StoryboardActionsBarProps = {
  onGenerate: () => void;
  onAutoRun: () => void;
  onSave?: () => void;
  isGenerating: boolean;
  isRendering: boolean;
  isAutoRunning: boolean;
  isSaving?: boolean;
  topicEmpty: boolean;
  autoRunStep: AutoRunStepId | "idle";
  showSave?: boolean;
};

const base =
  "rounded-md px-2.5 py-1 text-[10px] font-semibold transition disabled:opacity-40 disabled:cursor-not-allowed";

export default function StoryboardActionsBar({
  onGenerate,
  onAutoRun,
  onSave,
  isGenerating,
  isRendering,
  isAutoRunning,
  isSaving,
  topicEmpty,
  autoRunStep,
  showSave,
}: StoryboardActionsBarProps) {
  const currentStepLabel = AUTO_RUN_STEPS.find((s) => s.id === autoRunStep)?.label || "Running";

  return (
    <div className="flex items-center gap-1.5">
      <button
        data-testid="generate-btn"
        onClick={onGenerate}
        disabled={isGenerating || topicEmpty || isAutoRunning}
        className={`${base} border border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50`}
      >
        {isGenerating ? (
          <span className="flex items-center gap-1.5">
            <LoadingSpinner size="sm" color="text-zinc-400" />
            Wait...
          </span>
        ) : (
          "Generate"
        )}
      </button>
      <button
        onClick={onAutoRun}
        disabled={isGenerating || isRendering || isAutoRunning || topicEmpty}
        className={`${base} bg-zinc-900 text-white hover:bg-zinc-800`}
      >
        {isAutoRunning ? (
          <span className="flex items-center gap-1.5">
            <LoadingSpinner size="sm" color="text-white/70" />
            {currentStepLabel}...
          </span>
        ) : (
          "Auto Run"
        )}
      </button>
      {showSave && onSave && (
        <button
          onClick={onSave}
          disabled={isSaving}
          className={`${base} bg-emerald-500 text-white hover:bg-emerald-600`}
        >
          {isSaving ? "Saving..." : "Save"}
        </button>
      )}
    </div>
  );
}
