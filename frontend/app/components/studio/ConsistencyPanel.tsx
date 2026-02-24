"use client";

import { useState } from "react";
import { useContextStore } from "../../store/useContextStore";
import { useConsistency } from "../../hooks/useConsistency";
import { SIDE_PANEL_LABEL, ERROR_BG, ERROR_TEXT, ERROR_BORDER } from "../ui/variants";
import LoadingSpinner from "../ui/LoadingSpinner";
import DriftHeatmap from "./DriftHeatmap";
import DriftDetailView from "./DriftDetailView";
import type { SceneDriftResponse } from "../../types";

const LEGEND: { status: string; color: string }[] = [
  { status: "match", color: "bg-emerald-400" },
  { status: "mismatch", color: "bg-red-400" },
  { status: "missing", color: "bg-amber-400" },
  { status: "no_data", color: "bg-zinc-200" },
];

export default function ConsistencyPanel() {
  const storyboardId = useContextStore((s) => s.storyboardId);
  const { data, loading, error } = useConsistency(storyboardId);
  const [selectedScene, setSelectedScene] = useState<SceneDriftResponse | null>(null);

  if (!storyboardId) return null;

  const warningCount = data ? data.scenes.filter((s) => s.identity_score < 0.7).length : 0;

  return (
    <div>
      <label className={SIDE_PANEL_LABEL}>Consistency</label>

      {loading && (
        <div className="flex items-center justify-center py-4" data-testid="consistency-loading">
          <LoadingSpinner size="sm" />
        </div>
      )}

      {error && (
        <div
          className={`rounded-lg p-2 text-[11px] ${ERROR_BORDER} ${ERROR_BG} ${ERROR_TEXT}`}
          data-testid="consistency-error"
        >
          {error}
        </div>
      )}

      {!loading && !error && data && (
        <div className="space-y-2">
          {/* Summary */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-zinc-800" data-testid="overall-consistency">
              {Math.round(data.overall_consistency * 100)}%
            </span>
            <span className="text-[11px] text-zinc-400">overall</span>
            {warningCount > 0 && (
              <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[11px] font-semibold text-amber-700">
                {warningCount} warn
              </span>
            )}
          </div>

          {/* Legend */}
          <div className="flex gap-2">
            {LEGEND.map((item) => (
              <div key={item.status} className="flex items-center gap-1">
                <span className={`inline-block h-2.5 w-2.5 rounded-sm ${item.color}`} />
                <span className="text-[11px] text-zinc-400">{item.status}</span>
              </div>
            ))}
          </div>

          {/* Heatmap */}
          {data.scenes.length > 0 ? (
            <DriftHeatmap
              scenes={data.scenes}
              selectedSceneId={selectedScene?.scene_id ?? null}
              onSceneClick={setSelectedScene}
            />
          ) : (
            <div className="py-3 text-center text-[11px] text-zinc-400">
              No consistency data yet.
            </div>
          )}

          {/* Detail */}
          {selectedScene && (
            <DriftDetailView scene={selectedScene} onClose={() => setSelectedScene(null)} />
          )}
        </div>
      )}

      {!loading && !error && !data && (
        <div className="py-3 text-center text-[11px] text-zinc-400">No consistency data.</div>
      )}
    </div>
  );
}
