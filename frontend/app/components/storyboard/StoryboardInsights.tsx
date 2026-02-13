"use client";

import { SIDE_PANEL_LABEL } from "../ui/variants";
import { hasSceneImage } from "../../utils/sceneCompletion";

export type InsightScene = {
  script: string;
  duration: number;
  image_url: string | null;
  client_id: string;
  candidates?: Array<{ media_asset_id: number }>;
};

type SceneMatchRate = {
  match_rate?: number;
  missing?: string[];
};

type Props = {
  scenes: InsightScene[];
  imageValidationResults?: Record<string, SceneMatchRate>;
};

export default function StoryboardInsights({ scenes, imageValidationResults }: Props) {
  if (scenes.length === 0) return null;

  const total = scenes.length;
  const totalDuration = scenes.reduce((sum, s) => sum + (s.duration || 0), 0);
  const withScript = scenes.filter((s) => s.script.trim().length > 0).length;
  const withImage = scenes.filter((s) => hasSceneImage(s)).length;
  const complete = scenes.filter(
    (s) => s.script.trim().length > 0 && hasSceneImage(s)
  ).length;
  const completionPct = Math.round((complete / total) * 100);
  const imagePct = Math.round((withImage / total) * 100);
  const renderReady = withScript === total && withImage === total;

  let avgMatchRate: number | null = null;
  if (imageValidationResults) {
    const rates = scenes
      .map((s) => imageValidationResults[s.client_id]?.match_rate)
      .filter((r): r is number => r != null);
    if (rates.length > 0) {
      avgMatchRate = Math.round(rates.reduce((a, b) => a + b, 0) / rates.length);
    }
  }

  return (
    <div className="pb-3">
      <label className={SIDE_PANEL_LABEL}>Insights</label>
      <div className="grid grid-cols-2 gap-1.5">
        <Cell label="총 길이" value={`${totalDuration}초`} />
        <Cell
          label="씬 완성도"
          value={`${completionPct}%`}
          accent={completionPct === 100 ? "emerald" : undefined}
        />
        <Cell label="이미지" value={`${imagePct}%`} />
        <Cell
          label="Avg Match"
          value={avgMatchRate != null ? `${avgMatchRate}%` : "--"}
        />
      </div>
      <div
        className={`mt-1.5 rounded-lg px-2 py-1 text-center text-[11px] font-semibold ${
          renderReady ? "bg-emerald-50 text-emerald-700" : "bg-zinc-100 text-zinc-400"
        }`}
      >
        {renderReady ? "Render Ready" : "Not Ready"}
      </div>
    </div>
  );
}

/* ---- Sub-component ---- */

const ACCENT_MAP = {
  emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
} as const;

function Cell({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: keyof typeof ACCENT_MAP;
}) {
  const cls = accent ? ACCENT_MAP[accent] : "border-zinc-200 bg-zinc-50 text-zinc-600";
  return (
    <div className={`flex flex-col items-center rounded-lg border px-1.5 py-1 ${cls}`}>
      <span className="text-xs font-bold">{value}</span>
      <span className="text-[11px] text-zinc-400">{label}</span>
    </div>
  );
}
