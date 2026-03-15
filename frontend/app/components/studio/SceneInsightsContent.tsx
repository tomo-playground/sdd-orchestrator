"use client";

import StoryboardInsights, { type InsightScene } from "../storyboard/StoryboardInsights";
import ConsistencyPanel from "./ConsistencyPanel";
import {
  SIDE_PANEL_LABEL,
  SUCCESS_BG,
  SUCCESS_TEXT,
  SUCCESS_BORDER,
  WARNING_BG,
  WARNING_TEXT,
  WARNING_BORDER,
  ERROR_BG,
  ERROR_TEXT,
  ERROR_BORDER,
} from "../ui/variants";

type SceneMatchRate = {
  match_rate?: number;
  wd14_match_rate?: number;
  missing?: string[];
  gemini_tokens?: string[];
};

type SceneInsightsContentProps = {
  imageValidationResults?: Record<string, SceneMatchRate>;
  scenes?: { id: number; client_id: string; order?: number }[];
  onSceneSelect?: (index: number) => void;
  fullScenes?: InsightScene[];
};

export default function SceneInsightsContent({
  imageValidationResults,
  scenes: scenesInfo,
  onSceneSelect,
  fullScenes,
}: SceneInsightsContentProps) {
  const hasMatchRateGrid =
    scenesInfo &&
    scenesInfo.length > 0 &&
    imageValidationResults &&
    Object.keys(imageValidationResults).length > 0;

  return (
    <div className="space-y-4">
      {/* Storyboard Insights */}
      {fullScenes && fullScenes.length > 0 && (
        <StoryboardInsights scenes={fullScenes} imageValidationResults={imageValidationResults} />
      )}

      {/* Match Rate Grid */}
      {hasMatchRateGrid && (
        <div>
          <label className={SIDE_PANEL_LABEL}>Match Rates</label>
          <div className="grid grid-cols-3 gap-1.5">
            {scenesInfo!.map((scene, index) => {
              const result = imageValidationResults![scene.client_id];
              // Phase 33: prefer wd14_match_rate (immediate, stable)
              const rawRate = result?.wd14_match_rate ?? result?.match_rate;
              const rate = rawRate != null ? rawRate * 100 : null;
              const hasRate = rate !== null;
              const hasPending = (result?.gemini_tokens?.length ?? 0) > 0;
              const colorClass = !hasRate
                ? "border-zinc-200 bg-zinc-50 text-zinc-400"
                : rate! >= 90
                  ? `${SUCCESS_BORDER} ${SUCCESS_BG} ${SUCCESS_TEXT}`
                  : rate! >= 70
                    ? `${WARNING_BORDER} ${WARNING_BG} ${WARNING_TEXT}`
                    : `${ERROR_BORDER} ${ERROR_BG} ${ERROR_TEXT}`;

              return (
                <button
                  key={scene.client_id}
                  type="button"
                  onClick={() => onSceneSelect?.(index)}
                  title={
                    hasRate
                      ? `Scene ${index + 1}: ${Math.round(rate)}% match${hasPending ? ` (+${result.gemini_tokens!.length} pending)` : ""}`
                      : `Scene ${index + 1}: not validated`
                  }
                  className={`flex cursor-pointer flex-col items-center rounded-lg border px-1 py-1.5 text-[11px] leading-tight font-semibold transition-all hover:scale-105 ${colorClass}`}
                >
                  <span>S{index + 1}</span>
                  <span>{hasRate ? `${Math.round(rate)}%` : "--"}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Cross-Scene Consistency */}
      <ConsistencyPanel />
    </div>
  );
}
