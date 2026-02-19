"use client";

import type { QCAnalysis, QCIssue } from "../../types/creative";
import { RATING_LABELS, SEVERITY_LABELS, CATEGORY_LABELS } from "./qcLabels";

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
  const ratingLabel = RATING_LABELS[analysis.overall_rating] ?? analysis.overall_rating;

  return (
    <div className="space-y-3 rounded-xl border border-zinc-200 bg-white p-4">
      {/* Header: rating + score */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${ratingStyle.bg} ${ratingStyle.text}`}
          >
            {ratingLabel}
          </span>
          <span className="text-sm font-semibold text-zinc-700">
            품질 점수 {(analysis.score * 100).toFixed(0)}점
          </span>
        </div>
      </div>

      {/* Score breakdown */}
      <div className="grid grid-cols-3 gap-2">
        {Object.entries(analysis.score_breakdown).map(([key, value]) => (
          <div key={key} className="rounded-lg bg-zinc-50 px-2.5 py-2">
            <p className="text-xs text-zinc-500">{CATEGORY_LABELS[key] ?? key}</p>
            <div className="mt-1 flex items-center gap-1.5">
              <div className="h-1.5 flex-1 rounded-full bg-zinc-200">
                <div
                  className={`h-1.5 rounded-full ${
                    value >= 0.8 ? "bg-emerald-400" : value >= 0.5 ? "bg-amber-400" : "bg-red-400"
                  }`}
                  style={{ width: `${value * 100}%` }}
                />
              </div>
              <span className="text-xs font-medium text-zinc-600">{(value * 100).toFixed(0)}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="rounded-lg bg-zinc-50 px-3 py-2.5">
        <p className="mb-1 text-xs font-semibold text-zinc-400">분석 요약</p>
        <p className="text-sm leading-relaxed text-zinc-600">{analysis.summary}</p>
      </div>

      {/* Strengths */}
      {analysis.strengths.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-semibold tracking-wider text-emerald-600">강점</p>
          <ul className="space-y-1">
            {analysis.strengths.map((s, i) => (
              <li
                key={i}
                className="flex items-start gap-1.5 rounded-lg bg-emerald-50 px-2.5 py-1.5 text-sm text-zinc-700"
              >
                <span className="mt-0.5 text-emerald-500">✓</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Issues (sorted by severity) */}
      {analysis.issues.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-semibold tracking-wider text-zinc-400">
            개선점 ({analysis.issues.length}건)
          </p>
          <div className="space-y-2">
            {sortedIssues(analysis.issues).map((issue, i) => (
              <div
                key={i}
                className={`rounded-lg border px-3 py-2 ${SEVERITY_STYLES[issue.severity] ?? ""}`}
              >
                <div className="flex items-center gap-2">
                  <span className="rounded px-1.5 py-0.5 text-[11px] font-bold">
                    {SEVERITY_LABELS[issue.severity] ?? issue.severity}
                  </span>
                  <span className="text-xs text-zinc-500">
                    {CATEGORY_LABELS[issue.category] ?? issue.category}
                  </span>
                  <button
                    onClick={() => onSceneClick?.(issue.scene)}
                    className="ml-auto shrink-0 font-mono text-xs underline"
                  >
                    #{issue.scene}
                  </button>
                </div>
                <p className="mt-1 text-sm leading-relaxed text-zinc-700">{issue.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
