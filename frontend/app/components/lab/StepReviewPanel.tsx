"use client";

import { useState } from "react";
import type { StepReviewData } from "../../types/creative";

type Props = {
  review: StepReviewData;
  onAction?: (action: "approve" | "revise", feedback?: string) => void;
};

export default function StepReviewPanel({ review, onAction }: Props) {
  const [feedback, setFeedback] = useState("");
  const qc = review.qc_analysis;

  return (
    <div className="mt-3 space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
      {/* QC Score */}
      {qc && (
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-semibold text-zinc-500">QC Score</span>
          <span
            className={`rounded px-1.5 py-0.5 text-[12px] font-bold ${
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
            className={`rounded px-1.5 py-0.5 text-[12px] ${
              qc.overall_rating === "good"
                ? "bg-emerald-100 text-emerald-700"
                : qc.overall_rating === "needs_revision"
                  ? "bg-amber-100 text-amber-700"
                  : "bg-red-100 text-red-700"
            }`}
          >
            {qc.overall_rating}
          </span>
        </div>
      )}

      {/* Issues */}
      {qc?.issues && qc.issues.length > 0 && (
        <div className="space-y-1">
          <p className="text-[12px] font-semibold text-zinc-500">Issues</p>
          {qc.issues.map((issue, i) => (
            <div
              key={i}
              className={`rounded px-2 py-1 text-[12px] ${
                issue.severity === "critical"
                  ? "bg-red-50 text-red-700"
                  : issue.severity === "warning"
                    ? "bg-amber-50 text-amber-700"
                    : "bg-zinc-50 text-zinc-600"
              }`}
            >
              <span className="font-semibold uppercase">[{issue.severity}]</span> Scene{" "}
              {issue.scene}: {issue.description}
            </div>
          ))}
        </div>
      )}

      {/* Strengths */}
      {qc?.strengths && qc.strengths.length > 0 && (
        <div>
          <p className="text-[12px] font-semibold text-zinc-500">Strengths</p>
          {qc.strengths.map((s, i) => (
            <p key={i} className="text-[12px] text-emerald-700">
              {s}
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
            className="w-full rounded border border-zinc-200 bg-white px-2 py-1.5 text-[12px] text-zinc-800 focus:border-zinc-400 focus:outline-none"
          />
          <div className="flex gap-2">
            <button
              onClick={() => onAction("approve")}
              className="rounded bg-emerald-600 px-3 py-1 text-[12px] font-semibold text-white hover:bg-emerald-500"
            >
              Approve
            </button>
            <button
              onClick={() => onAction("revise", feedback || undefined)}
              className="rounded bg-amber-500 px-3 py-1 text-[12px] font-semibold text-white hover:bg-amber-400"
            >
              Request Revision
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
