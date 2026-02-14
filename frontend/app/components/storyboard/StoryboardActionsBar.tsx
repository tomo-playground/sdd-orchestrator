"use client";

import type { AutoRunStepId, Scene } from "../../types";
import { AUTO_RUN_STEPS } from "../../constants";
import LoadingSpinner from "../ui/LoadingSpinner";
import { Tooltip } from "../ui";

type StoryboardActionsBarProps = {
  onAutoRun: () => void;
  onSave?: () => void;
  isRendering: boolean;
  isAutoRunning: boolean;
  isSaving?: boolean;
  autoRunStep: AutoRunStepId | "idle";
  showSave?: boolean;
};

const base =
  "rounded-md px-2.5 py-1 text-[12px] font-semibold transition disabled:opacity-40 disabled:cursor-not-allowed";

export default function StoryboardActionsBar({
  onAutoRun,
  onSave,
  isRendering,
  isAutoRunning,
  isSaving,
  autoRunStep,
  showSave,
}: StoryboardActionsBarProps) {
  const currentStepLabel = AUTO_RUN_STEPS.find((s) => s.id === autoRunStep)?.label || "Running";

  return (
    <div className="flex items-center gap-1.5">
      <Tooltip content="Automatically generate assets (Cmd+Enter)" position="bottom">
        <button
          onClick={onAutoRun}
          disabled={isRendering || isAutoRunning}
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
      </Tooltip>
      {showSave && onSave && (
        <Tooltip content="Save storyboard (Cmd+S)" position="bottom">
          <button
            onClick={onSave}
            disabled={isSaving}
            className={`${base} bg-emerald-500 text-white hover:bg-emerald-600`}
          >
            {isSaving ? "Saving..." : "Save"}
          </button>
        </Tooltip>
      )}
    </div>
  );
}
