"use client";

import { useState } from "react";
import NarrativeScoreChart from "../NarrativeScoreChart";
import type { NarrativeScore } from "../../../types";

function isNarrativeScore(v: unknown): v is NarrativeScore {
  return typeof v === "object" && v !== null && "overall" in v;
}

type SectionProps = { data: Record<string, unknown> };

export function CriticSection({ data }: SectionProps) {
  const candidates = (data.candidates ?? []) as Array<Record<string, unknown>>;
  const evaluation = data.evaluation as Record<string, unknown> | undefined;

  return (
    <div className="space-y-2">
      {candidates.length > 0 && (
        <div className="space-y-1">
          <p className="text-[11px] font-medium text-zinc-500">후보 컨셉</p>
          {candidates.map((c, i) => (
            <div key={i} className="rounded-lg bg-zinc-50 px-3 py-2">
              <p className="text-xs font-medium text-zinc-700">
                {String(c.agent_role ?? "")} — {String(c.title ?? "")}
              </p>
              <p className="mt-0.5 text-[11px] text-zinc-500">{String(c.concept ?? "")}</p>
            </div>
          ))}
        </div>
      )}
      {evaluation && (
        <p className="text-[11px] text-zinc-500">
          추천:{" "}
          <span className="font-medium text-zinc-700">
            {String(evaluation.best_agent_role ?? "")}
          </span>
        </p>
      )}
    </div>
  );
}

export function ReviewSection({ data }: SectionProps) {
  const passed = data.passed as boolean | undefined;
  const narrativeScore = isNarrativeScore(data.narrative_score) ? data.narrative_score : undefined;
  const errors = (data.errors ?? []) as string[];
  const warnings = (data.warnings ?? []) as string[];
  const userSummary = data.user_summary as string | undefined;
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span
          className={`rounded px-2 py-0.5 text-[11px] font-medium ${
            passed ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
          }`}
        >
          {passed ? "PASSED" : "FAILED"}
        </span>
        {errors.length > 0 && (
          <span className="text-[11px] text-red-500">{errors.length} errors</span>
        )}
        {warnings.length > 0 && (
          <span className="text-[11px] text-amber-500">{warnings.length} warnings</span>
        )}
      </div>
      {userSummary && (
        <p className="text-xs text-zinc-600">{userSummary}</p>
      )}
      {(errors.length > 0 || warnings.length > 0) && (
        <div>
          <button
            type="button"
            className="text-[11px] text-zinc-400 hover:text-zinc-600"
            onClick={() => setShowDetails((v) => !v)}
          >
            {showDetails ? "상세 접기" : "상세 보기"}
          </button>
          {showDetails && (
            <ul className="mt-1 space-y-0.5">
              {errors.map((e, i) => (
                <li key={`e-${i}`} className="text-[11px] text-red-500">
                  {e}
                </li>
              ))}
              {warnings.map((w, i) => (
                <li key={`w-${i}`} className="text-[11px] text-amber-500">
                  {w}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {narrativeScore && <NarrativeScoreChart score={narrativeScore} />}
    </div>
  );
}

export function DirectorSection({ data }: SectionProps) {
  const decision = data.decision ? String(data.decision) : null;
  const feedback = data.feedback ? String(data.feedback) : null;
  return (
    <div className="space-y-1">
      {decision && (
        <p className="text-xs">
          <span className="font-medium text-zinc-600">결정: </span>
          <span
            className={`font-semibold ${
              decision === "approve" ? "text-emerald-600" : "text-amber-600"
            }`}
          >
            {decision}
          </span>
        </p>
      )}
      {feedback && (
        <p className="text-[11px] leading-relaxed text-zinc-500">{feedback}</p>
      )}
    </div>
  );
}

export function ExplainSection({ data }: SectionProps) {
  const text = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  return <p className="text-[11px] leading-relaxed whitespace-pre-wrap text-zinc-600">{text}</p>;
}

const SECTION_RENDERERS: Record<string, React.ComponentType<SectionProps>> = {
  critic: CriticSection,
  review: ReviewSection,
  director: DirectorSection,
  explain: ExplainSection,
};

export function renderSectionContent(id: string, data: Record<string, unknown>) {
  const Component = SECTION_RENDERERS[id];
  return Component ? <Component data={data} /> : null;
}
