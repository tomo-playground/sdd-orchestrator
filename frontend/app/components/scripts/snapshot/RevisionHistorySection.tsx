"use client";

import type { RevisionHistoryEntry } from "../../../types";

type Props = {
  history: RevisionHistoryEntry[];
};

const TIER_COLORS: Record<string, string> = {
  rule_fix: "bg-emerald-100 text-emerald-700",
  expansion: "bg-sky-100 text-sky-700",
  regeneration: "bg-amber-100 text-amber-700",
};

export default function RevisionHistorySection({ history }: Props) {
  if (!history || history.length === 0) return null;

  return (
    <div className="space-y-2">
      {history.map((entry, i) => {
        const tierCls = TIER_COLORS[entry.tier ?? ""] ?? "bg-zinc-100 text-zinc-600";
        const scorePct = entry.score != null ? Math.round(entry.score * 100) : null;

        return (
          <div key={i} className="flex items-start gap-2">
            {/* Timeline dot */}
            <div className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-zinc-300" />

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] font-medium text-zinc-600">#{entry.attempt}</span>
                {entry.tier && (
                  <span className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${tierCls}`}>
                    {entry.tier}
                  </span>
                )}
                {scorePct != null && <span className="text-[11px] text-zinc-500">{scorePct}%</span>}
              </div>

              {entry.errors && entry.errors.length > 0 && (
                <ul className="mt-1 space-y-0.5">
                  {entry.errors.map((err, j) => (
                    <li key={j} className="text-[11px] leading-relaxed text-red-600">
                      {err}
                    </li>
                  ))}
                </ul>
              )}

              {entry.warnings && entry.warnings.length > 0 && (
                <ul className="mt-1 space-y-0.5">
                  {entry.warnings.map((w, j) => (
                    <li key={j} className="text-[11px] leading-relaxed text-amber-600">
                      {w}
                    </li>
                  ))}
                </ul>
              )}

              {entry.narrative_score != null && (
                <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">
                  서사 점수 {Math.round(entry.narrative_score.overall * 100)}%
                  {entry.narrative_score.feedback && ` · ${entry.narrative_score.feedback}`}
                </p>
              )}

              {entry.reflection && (
                <p className="mt-1 text-[11px] leading-relaxed text-zinc-500">{entry.reflection}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
