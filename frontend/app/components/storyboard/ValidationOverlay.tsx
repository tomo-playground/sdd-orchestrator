"use client";

import type { ImageValidation, CriticalFailureItem } from "../../types";

function formatCriticalFailure(f: CriticalFailureItem): string {
  if (f.failure_type === "gender_swap") return `성별 반전: ${f.expected} → ${f.detected}`;
  if (f.failure_type === "no_subject") return `인물 미감지 (expected: ${f.expected})`;
  return `인물수 불일치: ${f.expected}명 → ${f.detected}명`;
}

type ValidationOverlayProps = {
  result?: ImageValidation;
  isValidating: boolean;
  onValidate: () => void;
  onApplyMissingTags?: (tags: string[]) => void;
};

export default function ValidationOverlay({
  result,
  isValidating,
  onValidate,
  onApplyMissingTags,
}: ValidationOverlayProps) {
  if (!result) {
    return (
      <div className="flex flex-col items-center gap-2">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onValidate();
          }}
          disabled={isValidating}
          className="rounded-full bg-white/90 px-4 py-2 text-[12px] font-semibold tracking-[0.15em] uppercase shadow-sm backdrop-blur transition hover:bg-white disabled:opacity-50"
        >
          {isValidating ? "Validating..." : "Run Validation"}
        </button>
      </div>
    );
  }

  const rate = Math.round((result.match_rate ?? 0) * 100);
  const missingCount = result.missing?.length ?? 0;
  const extraCount = result.extra?.length ?? 0;
  const criticalFailures = result.critical_failure?.failures ?? [];
  const rateColor =
    rate >= 80 ? "text-emerald-400" : rate >= 50 ? "text-amber-400" : "text-red-400";
  const barColor = rate >= 80 ? "bg-emerald-400" : rate >= 50 ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="flex w-full flex-col gap-2 px-4">
      {/* Critical Failure Warning */}
      {criticalFailures.length > 0 && (
        <div className="rounded-lg bg-red-500/80 px-3 py-2 backdrop-blur">
          {criticalFailures.map((f: CriticalFailureItem, i: number) => (
            <p key={i} className="text-[12px] font-bold text-white">
              {formatCriticalFailure(f)}
            </p>
          ))}
        </div>
      )}

      {/* Match Rate */}
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/20">
          <div className={`h-full rounded-full ${barColor}`} style={{ width: `${rate}%` }} />
        </div>
        <span className={`text-lg font-bold ${rateColor}`}>{rate}%</span>
      </div>

      {/* Missing / Extra counts */}
      <div className="flex gap-3 text-[12px] font-semibold tracking-wider">
        {missingCount > 0 && <span className="text-red-300">MISSING {missingCount}</span>}
        {extraCount > 0 && <span className="text-amber-300">EXTRA {extraCount}</span>}
        {missingCount === 0 && extraCount === 0 && criticalFailures.length === 0 && (
          <span className="text-emerald-300">PERFECT MATCH</span>
        )}
      </div>

      {/* Missing tags preview */}
      {missingCount > 0 && result.missing && (
        <p className="line-clamp-2 text-[12px] text-white/60">
          {result.missing.slice(0, 5).join(", ")}
          {missingCount > 5 && ` +${missingCount - 5}`}
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onValidate();
          }}
          disabled={isValidating}
          className="rounded-full bg-white/20 px-3 py-1 text-[11px] font-semibold tracking-wider text-white uppercase backdrop-blur transition hover:bg-white/30 disabled:opacity-50"
        >
          {isValidating ? "..." : "Re-validate"}
        </button>
        {missingCount > 0 && onApplyMissingTags && result.missing && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onApplyMissingTags(result.missing!);
            }}
            className="rounded-full bg-red-500/70 px-3 py-1 text-[11px] font-semibold tracking-wider text-white uppercase backdrop-blur transition hover:bg-red-500/90"
          >
            + Add Missing
          </button>
        )}
      </div>
    </div>
  );
}
