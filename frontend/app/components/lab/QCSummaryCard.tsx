"use client";

import type { QCAnalysis, QCIssue } from "../../types/creative";

const RATING_STYLES: Record<string, { bg: string; text: string }> = {
  good: { bg: "bg-emerald-100", text: "text-emerald-700" },
  needs_revision: { bg: "bg-amber-100", text: "text-amber-700" },
  poor: { bg: "bg-red-100", text: "text-red-700" },
};

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  warning: 1,
  suggestion: 2,
};

const SEVERITY_STYLES: Record<string, string> = {
  critical: "text-red-600 bg-red-50 border-red-200",
  warning: "text-amber-600 bg-amber-50 border-amber-200",
  suggestion: "text-blue-600 bg-blue-50 border-blue-200",
};

const SCORE_LABELS: Record<string, string> = {
  readability: "Readability",
  hook_strength: "Hook Strength",
  emotional_arc: "Emotional Arc",
  tts_naturalness: "TTS Natural",
  expression_diversity: "Diversity",
  consistency: "Consistency",
};

type Props = {
  analysis: QCAnalysis;
  onSceneClick?: (scene: number) => void;
};

function sortedIssues(issues: QCIssue[]): QCIssue[] {
  return [...issues].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
  );
}

export default function QCSummaryCard({ analysis, onSceneClick }: Props) {
  const ratingStyle = RATING_STYLES[analysis.overall_rating] ?? RATING_STYLES.poor;

  return (
    <div className="space-y-3 rounded-xl border border-zinc-200 bg-white p-4">
      {/* Header: rating + score */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${ratingStyle.bg} ${ratingStyle.text}`}
          >
            {analysis.overall_rating.replace("_", " ")}
          </span>
          <span className="text-xs font-semibold text-zinc-700">
            Score: {(analysis.score * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Score breakdown */}
      <div className="grid grid-cols-3 gap-2">
        {Object.entries(analysis.score_breakdown).map(([key, value]) => (
          <div key={key} className="rounded-lg bg-zinc-50 px-2 py-1.5">
            <p className="text-[10px] text-zinc-400">{SCORE_LABELS[key] ?? key}</p>
            <div className="mt-0.5 flex items-center gap-1.5">
              <div className="h-1.5 flex-1 rounded-full bg-zinc-200">
                <div
                  className={`h-1.5 rounded-full ${
                    value >= 0.8 ? "bg-emerald-400" : value >= 0.5 ? "bg-amber-400" : "bg-red-400"
                  }`}
                  style={{ width: `${value * 100}%` }}
                />
              </div>
              <span className="text-[10px] font-medium text-zinc-600">
                {(value * 100).toFixed(0)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <p className="text-xs text-zinc-600">{analysis.summary}</p>

      {/* Strengths */}
      {analysis.strengths.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] font-semibold tracking-wider text-emerald-600 uppercase">
            Strengths
          </p>
          <ul className="space-y-0.5">
            {analysis.strengths.map((s, i) => (
              <li key={i} className="text-[11px] text-zinc-600">
                + {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Issues (sorted by severity) */}
      {analysis.issues.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Issues ({analysis.issues.length})
          </p>
          <div className="space-y-1">
            {sortedIssues(analysis.issues).map((issue, i) => (
              <div
                key={i}
                className={`flex items-start gap-2 rounded-lg border px-2.5 py-1.5 text-[11px] ${SEVERITY_STYLES[issue.severity] ?? ""}`}
              >
                <span className="font-bold uppercase">{issue.severity[0]}</span>
                <div className="flex-1">
                  <span className="text-zinc-500">[{issue.category}]</span> {issue.description}
                </div>
                <button
                  onClick={() => onSceneClick?.(issue.scene)}
                  className="shrink-0 font-mono text-[10px] underline"
                >
                  #{issue.scene}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
