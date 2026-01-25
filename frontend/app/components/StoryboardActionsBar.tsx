"use client";

import type { AutoRunStepId } from "../types";
import { AUTO_RUN_STEPS } from "../constants";
import LoadingSpinner from "./LoadingSpinner";

type StoryboardActionsBarProps = {
  // Reset actions
  onResetScenes: () => void;
  onResetDraft: () => void;
  // Primary actions
  onGenerate: () => void;
  onAutoRun: () => void;
  // State
  isGenerating: boolean;
  isRendering: boolean;
  isAutoRunning: boolean;
  topicEmpty: boolean;
  autoRunStep: AutoRunStepId | "idle";
};

export default function StoryboardActionsBar({
  onResetScenes,
  onResetDraft,
  onGenerate,
  onAutoRun,
  isGenerating,
  isRendering,
  isAutoRunning,
  topicEmpty,
  autoRunStep,
}: StoryboardActionsBarProps) {
  const currentStepLabel = AUTO_RUN_STEPS.find((s) => s.id === autoRunStep)?.label || "Running";

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      {/* Reset Actions - Left */}
      <div className="flex items-center gap-2">
        <button
          onClick={onResetScenes}
          disabled={isAutoRunning}
          className="rounded-full border border-zinc-200 bg-white/60 px-3 py-1.5 text-[10px] font-medium tracking-[0.15em] text-zinc-500 uppercase transition hover:border-zinc-300 hover:text-zinc-600 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Reset Scenes
        </button>
        <button
          onClick={onResetDraft}
          disabled={isAutoRunning}
          className="rounded-full border border-zinc-200 bg-white/60 px-3 py-1.5 text-[10px] font-medium tracking-[0.15em] text-zinc-500 uppercase transition hover:border-zinc-300 hover:text-zinc-600 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Reset Draft
        </button>
      </div>
      {/* Primary Actions - Right */}
      <div className="flex items-center gap-2">
        <button
          onClick={onGenerate}
          disabled={isGenerating || topicEmpty || isAutoRunning}
          className="min-w-[120px] rounded-full border border-zinc-300 bg-white px-5 py-2 text-xs font-semibold tracking-[0.2em] text-zinc-700 uppercase shadow-sm transition hover:bg-zinc-50 hover:border-zinc-400 disabled:cursor-not-allowed disabled:bg-zinc-100 disabled:text-zinc-400"
        >
          {isGenerating ? (
            <div className="flex items-center justify-center gap-2">
              <LoadingSpinner size="sm" color="text-zinc-400" />
              <span>Wait...</span>
            </div>
          ) : (
            "Generate"
          )}
        </button>
        <button
          onClick={onAutoRun}
          disabled={isGenerating || isRendering || isAutoRunning || topicEmpty}
          className="min-w-[140px] rounded-full bg-zinc-900 px-6 py-2 text-xs font-semibold tracking-[0.2em] text-white uppercase shadow-lg shadow-zinc-900/20 transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
        >
          {isAutoRunning ? (
            <div className="flex items-center justify-center gap-2">
              <LoadingSpinner size="sm" color="text-white/70" />
              <span>{currentStepLabel}...</span>
            </div>
          ) : (
            "Auto Run"
          )}
        </button>
      </div>
    </div>
  );
}
