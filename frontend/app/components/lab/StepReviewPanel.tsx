"use client";

import { useState } from "react";
import type { StepReviewData } from "../../types/creative";
import { RATING_LABELS, SEVERITY_LABELS, CATEGORY_LABELS } from "./qcLabels";

type Props = {
  review: StepReviewData;
  onAction?: (action: "approve" | "revise", feedback?: string) => void;
};

export default function StepReviewPanel({ review, onAction }: Props) {
  const [feedback, setFeedback] = useState("");
  const qc = review.qc_analysis;

  return (
    <div className="mt-3 space-y-2.5 rounded-lg border border-amber-200 bg-amber-50 p-4">
      {/* QC Score */}
      {qc && (
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-zinc-500">품질 점수</span>
          <span
            className={`rounded px-1.5 py-0.5 text-xs font-bold ${
              qc.score >= 0.85
                ? "bg-emerald-100 text-emerald-700"
                : qc.score >= 0.6
                  ? "bg-amber-100 text-amber-700"
                  : "bg-red-100 text-red-700"
            }`}
          >
            {(qc.score * 100).toFixed(0)}
          </span>
          <span
            className={`rounded px-1.5 py-0.5 text-xs ${
              qc.overall_rating === "good"
                ? "bg-emerald-100 text-emerald-700"
                : qc.overall_rating === "needs_revision"
                  ? "bg-amber-100 text-amber-700"
                  : "bg-red-100 text-red-700"
            }`}
          >
            {RATING_LABELS[qc.overall_rating] ?? qc.overall_rating}
          </span>
        </div>
      )}

      {/* Issues */}
      {qc?.issues && qc.issues.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-semibold text-zinc-500">개선점 ({qc.issues.length}건)</p>
          {qc.issues.map((issue, i) => (
            <div
              key={i}
              className={`rounded-lg px-2.5 py-1.5 ${
                issue.severity === "critical"
                  ? "bg-red-50 text-red-700"
                  : issue.severity === "warning"
                    ? "bg-amber-50 text-amber-700"
                    : "bg-zinc-50 text-zinc-600"
              }`}
            >
              <div className="flex items-center gap-1.5 text-xs">
                <span className="font-bold">
                  {SEVERITY_LABELS[issue.severity] ?? issue.severity}
                </span>
                <span className="text-zinc-400">
                  {CATEGORY_LABELS[issue.category] ?? issue.category}
                </span>
                <span className="ml-auto font-mono text-zinc-400">#{issue.scene}</span>
              </div>
              <p className="mt-0.5 text-sm leading-relaxed">{issue.description}</p>
            </div>
          ))}
        </div>
      )}

      {/* Strengths */}
      {qc?.strengths && qc.strengths.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-zinc-500">강점</p>
          {qc.strengths.map((s, i) => (
            <p
              key={i}
              className="flex items-start gap-1.5 rounded-lg bg-emerald-50 px-2.5 py-1.5 text-sm text-emerald-700"
            >
              <span className="mt-0.5">✓</span>
              <span>{s}</span>
            </p>
          ))}
        </div>
      )}

      {/* Feedback + Actions */}
      {onAction && (
        <div className="space-y-2 border-t border-amber-200 pt-2">
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="피드백을 입력하세요... (optional)"
            rows={2}
            className="w-full rounded border border-zinc-200 bg-white px-2.5 py-2 text-sm text-zinc-800 focus:border-zinc-400 focus:outline-none"
          />
          <div className="flex gap-2">
            <button
              onClick={() => onAction("approve")}
              className="rounded bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500"
            >
              승인
            </button>
            <button
              onClick={() => onAction("revise", feedback || undefined)}
              className="rounded bg-amber-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-amber-400"
            >
              수정 요청
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
