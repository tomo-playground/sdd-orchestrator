"use client";

import StoryboardInsights, { type InsightScene } from "../storyboard/StoryboardInsights";
import { SIDE_PANEL_LABEL } from "../ui/variants";

type SceneMatchRate = {
  match_rate?: number;
  missing?: string[];
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
              const rate = result?.match_rate;
              const hasRate = rate !== undefined && rate !== null;
              const colorClass = !hasRate
                ? "border-zinc-200 bg-zinc-50 text-zinc-400"
                : rate >= 80
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : rate >= 60
                    ? "border-amber-200 bg-amber-50 text-amber-700"
                    : "border-rose-200 bg-rose-50 text-rose-700";

              return (
                <button
                  key={scene.client_id}
                  type="button"
                  onClick={() => onSceneSelect?.(index)}
                  title={
                    hasRate
                      ? `Scene ${index + 1}: ${Math.round(rate)}% match`
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
    </div>
  );
}
