"use client";

import type { QualityGate } from "../../../types";

type Props = {
  qualityGate?: QualityGate;
  revisionCount?: number;
};

const PASS_BADGE = "bg-emerald-100 text-emerald-700";
const FAIL_BADGE = "bg-red-100 text-red-700";

export default function SnapshotSummaryHeader({ qualityGate, revisionCount }: Props) {
  if (!qualityGate) return null;

  const overallPct = qualityGate.narrative_score?.overall
    ? Math.round(qualityGate.narrative_score.overall * 100)
    : null;

  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      {/* Review pass/fail */}
      {qualityGate.review_passed != null && (
        <span
          className={`rounded px-2 py-0.5 text-[11px] font-medium ${
            qualityGate.review_passed ? PASS_BADGE : FAIL_BADGE
          }`}
        >
          {qualityGate.review_passed ? "PASS" : "FAIL"}
        </span>
      )}

      {/* Narrative overall score */}
      {overallPct != null && (
        <span className="text-[11px] text-zinc-500">
          서사 점수 <span className="font-medium text-zinc-700">{overallPct}%</span>
        </span>
      )}

      {/* Checkpoint score */}
      {qualityGate.checkpoint_score != null && (
        <span className="text-[11px] text-zinc-500">
          체크포인트{" "}
          <span className="font-medium text-zinc-700">
            {qualityGate.checkpoint_score.toFixed(2)}
          </span>
        </span>
      )}

      {/* Revision count */}
      {revisionCount != null && revisionCount > 0 && (
        <span className="text-[11px] text-zinc-500">
          수정 <span className="font-medium text-zinc-700">{revisionCount}회</span>
        </span>
      )}
    </div>
  );
}
