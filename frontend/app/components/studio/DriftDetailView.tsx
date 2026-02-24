"use client";

import type { DriftStatus, SceneDriftResponse } from "../../types";

const STATUS_BADGE: Record<DriftStatus, { label: string; classes: string }> = {
  match: { label: "Match", classes: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  mismatch: { label: "Mismatch", classes: "bg-red-50 text-red-700 border-red-200" },
  missing: { label: "Missing", classes: "bg-amber-50 text-amber-700 border-amber-200" },
  extra: { label: "Extra", classes: "bg-indigo-50 text-indigo-700 border-indigo-200" },
  no_data: { label: "No Data", classes: "bg-zinc-50 text-zinc-500 border-zinc-200" },
};

type DriftDetailViewProps = {
  scene: SceneDriftResponse;
  onClose: () => void;
};

export default function DriftDetailView({ scene, onClose }: DriftDetailViewProps) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-3" data-testid="drift-detail">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-zinc-700">
          Scene {scene.scene_order} — ID {Math.round(scene.identity_score * 100)}%
        </span>
        <button
          onClick={onClose}
          className="text-[11px] text-zinc-400 hover:text-zinc-600"
          aria-label="Close detail"
        >
          Close
        </button>
      </div>
      <div className="space-y-1.5">
        {scene.groups.map((g) => {
          const badge = STATUS_BADGE[(g.status as DriftStatus) ?? "no_data"];
          return (
            <div key={g.group} className="rounded border border-zinc-100 px-2 py-1.5">
              <div className="mb-1 flex items-center gap-1.5">
                <span className="text-[11px] font-medium text-zinc-600">{g.group}</span>
                <span
                  className={`rounded border px-1.5 py-0.5 text-[11px] leading-none font-semibold ${badge.classes}`}
                  data-testid={`badge-${g.group}`}
                >
                  {badge.label}
                </span>
              </div>
              <div className="flex gap-3 text-[11px]">
                <div>
                  <span className="text-zinc-400">Base: </span>
                  <span className="text-zinc-600" data-testid={`baseline-${g.group}`}>
                    {g.baseline_tags.length > 0 ? g.baseline_tags.join(", ") : "—"}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-400">Det: </span>
                  <span className="text-zinc-600" data-testid={`detected-${g.group}`}>
                    {g.detected_tags.length > 0 ? g.detected_tags.join(", ") : "—"}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
