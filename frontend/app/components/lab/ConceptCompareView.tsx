"use client";

import { useState } from "react";
import { Check, ChevronDown, ChevronUp, Star } from "lucide-react";
import type { ConceptCandidate } from "../../types/creative";

type Props = {
  candidates: ConceptCandidate[];
  evaluationSummary: string;
  selectedIndex: number | null;
  onSelect: (index: number) => void;
  isAutoSelected?: boolean;
};

const ROLE_COLORS: Record<string, { border: string; bg: string; badge: string }> = {
  emotional_arc: {
    border: "border-orange-300",
    bg: "bg-orange-50",
    badge: "bg-orange-100 text-orange-700",
  },
  visual_hook: { border: "border-blue-300", bg: "bg-blue-50", badge: "bg-blue-100 text-blue-700" },
  narrative_twist: {
    border: "border-purple-300",
    bg: "bg-purple-50",
    badge: "bg-purple-100 text-purple-700",
  },
};

const ROLE_LABELS: Record<string, string> = {
  emotional_arc: "Emotional Arc",
  visual_hook: "Visual Hook",
  narrative_twist: "Narrative Twist",
};

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-zinc-200">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[12px] font-semibold text-zinc-600">{score.toFixed(2)}</span>
    </div>
  );
}

function ConceptCard({
  candidate,
  isSelected,
  isBest,
  onSelect,
}: {
  candidate: ConceptCandidate;
  isSelected: boolean;
  isBest: boolean;
  onSelect: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const colors = ROLE_COLORS[candidate.agent_role] ?? {
    border: "border-zinc-300",
    bg: "bg-zinc-50",
    badge: "bg-zinc-100 text-zinc-700",
  };
  const label = ROLE_LABELS[candidate.agent_role] ?? candidate.agent_role;
  const c = candidate.concept;

  return (
    <div
      className={`rounded-xl border-2 p-4 transition ${
        isSelected ? "border-emerald-400 ring-2 ring-emerald-100" : colors.border
      } ${colors.bg}`}
    >
      {/* Header */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`rounded px-1.5 py-0.5 text-[12px] font-semibold ${colors.badge}`}>
            {label}
          </span>
          {isBest && (
            <span className="flex items-center gap-0.5 text-[12px] font-semibold text-emerald-600">
              <Star className="h-3 w-3" /> Recommended
            </span>
          )}
        </div>
        <ScoreBar score={candidate.score} />
      </div>

      {/* Title + Hook */}
      <h4 className="text-sm font-semibold text-zinc-800">{c.title}</h4>
      <p className="mt-1 text-xs text-zinc-600">{c.hook}</p>
      <p className="mt-1 text-[12px] text-zinc-400">Arc: {c.arc}</p>

      {/* Expand/Collapse */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-2 flex items-center gap-1 text-[12px] text-zinc-500 hover:text-zinc-700"
      >
        {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        {expanded ? "Less" : "Details"}
      </button>

      {expanded && (
        <div className="mt-2 space-y-2 border-t border-zinc-200 pt-2">
          {c.mood_progression && (
            <p className="text-[12px] text-zinc-500">
              <strong>Mood:</strong> {c.mood_progression}
            </p>
          )}
          {c.pacing_note && (
            <p className="text-[12px] text-zinc-500">
              <strong>Pacing:</strong> {c.pacing_note}
            </p>
          )}
          {c.key_moments && c.key_moments.length > 0 && (
            <div>
              <p className="text-[12px] font-semibold text-zinc-500">Key Moments:</p>
              <ul className="mt-0.5 ml-3 list-disc text-[12px] text-zinc-500">
                {c.key_moments.map((m, i) => (
                  <li key={i}>
                    <strong>{m.beat}</strong>: {m.description}
                    {m.camera_hint && <span className="text-zinc-400"> ({m.camera_hint})</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {candidate.feedback && (
            <p className="text-[12px] text-zinc-500">
              <strong>Feedback:</strong> {candidate.feedback}
            </p>
          )}
        </div>
      )}

      {/* Select button */}
      <button
        onClick={onSelect}
        disabled={isSelected}
        className={`mt-3 flex w-full items-center justify-center gap-1 rounded-lg py-1.5 text-xs font-semibold transition ${
          isSelected
            ? "bg-emerald-600 text-white"
            : "border border-zinc-300 bg-white text-zinc-600 hover:bg-zinc-50"
        }`}
      >
        {isSelected ? (
          <>
            <Check className="h-3.5 w-3.5" /> Selected
          </>
        ) : (
          "Select"
        )}
      </button>
    </div>
  );
}

export default function ConceptCompareView({
  candidates,
  evaluationSummary,
  selectedIndex,
  onSelect,
  isAutoSelected,
}: Props) {
  if (candidates.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-xl border border-dashed border-zinc-300 text-xs text-zinc-400">
        No concepts generated yet
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {evaluationSummary && (
        <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
          {evaluationSummary}
        </div>
      )}
      {isAutoSelected && selectedIndex !== null && (
        <div className="flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 px-3 py-2">
          <span className="text-xs font-semibold text-blue-700">
            Director auto-selected: Concept {String.fromCharCode(65 + selectedIndex)}
            {candidates[selectedIndex] && ` (score: ${candidates[selectedIndex].score.toFixed(2)})`}
          </span>
          <button
            onClick={() => onSelect(selectedIndex === 0 ? 1 : 0)}
            className="rounded border border-blue-300 px-2 py-0.5 text-[12px] font-semibold text-blue-600 hover:bg-blue-100"
          >
            Override
          </button>
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-3">
        {candidates.map((c, i) => (
          <ConceptCard
            key={c.agent_role}
            candidate={c}
            isSelected={selectedIndex === i}
            isBest={i === 0}
            onSelect={() => onSelect(i)}
          />
        ))}
      </div>
    </div>
  );
}
