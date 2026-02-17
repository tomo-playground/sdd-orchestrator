"use client";

import type { NarrativeScore } from "../../types";

type MetricDef = { key: keyof NarrativeScore; label: string };

const METRICS: MetricDef[] = [
  { key: "hook", label: "Hook 강도" },
  { key: "emotional_arc", label: "감정 곡선" },
  { key: "twist_payoff", label: "반전/결말" },
  { key: "speaker_tone", label: "화자 톤" },
  { key: "script_image_sync", label: "스크립트-이미지" },
];

function barColor(value: number): string {
  if (value >= 0.8) return "bg-emerald-500";
  if (value >= 0.6) return "bg-amber-400";
  return "bg-red-500";
}

function textColor(value: number): string {
  if (value >= 0.8) return "text-emerald-700";
  if (value >= 0.6) return "text-amber-700";
  return "text-red-700";
}

type Props = {
  score: NarrativeScore;
  compact?: boolean;
};

export default function NarrativeScoreChart({ score, compact }: Props) {
  if (compact) {
    return (
      <div className="flex items-center gap-2 text-xs">
        <span className="text-zinc-500">서사 품질</span>
        <div className="h-1.5 w-20 overflow-hidden rounded-full bg-zinc-100">
          <div
            className={`h-full rounded-full transition-all ${barColor(score.overall)}`}
            style={{ width: `${score.overall * 100}%` }}
          />
        </div>
        <span className={`font-medium ${textColor(score.overall)}`}>
          {Math.round(score.overall * 100)}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-zinc-600">서사 품질 분석</h4>
      {METRICS.map(({ key, label }) => {
        const val = (score[key] as number) ?? 0;
        return (
          <div key={key} className="flex items-center gap-2">
            <span className="w-24 text-[11px] text-zinc-500">{label}</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-zinc-100">
              <div
                className={`h-full rounded-full transition-all ${barColor(val)}`}
                style={{ width: `${val * 100}%` }}
              />
            </div>
            <span className={`w-8 text-right text-[11px] font-medium ${textColor(val)}`}>
              {Math.round(val * 100)}
            </span>
          </div>
        );
      })}
      {/* Overall */}
      <div className="mt-1 flex items-center gap-2 border-t border-zinc-100 pt-2">
        <span className="w-24 text-[11px] font-semibold text-zinc-700">종합</span>
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-100">
          <div
            className={`h-full rounded-full transition-all ${barColor(score.overall)}`}
            style={{ width: `${score.overall * 100}%` }}
          />
        </div>
        <span className={`w-8 text-right text-xs font-bold ${textColor(score.overall)}`}>
          {Math.round(score.overall * 100)}
        </span>
      </div>
      {score.feedback && (
        <p className="mt-1 text-[11px] leading-relaxed text-zinc-500">{score.feedback}</p>
      )}
    </div>
  );
}
