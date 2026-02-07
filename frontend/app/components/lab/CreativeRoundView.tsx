"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { Loader2, Trophy, MessageSquare } from "lucide-react";
import { API_BASE } from "../../constants";
import type {
  CreativeRound,
  CreativeTrace,
  CreativeTimeline,
} from "../../types/creative";
import TraceTimeline from "./TraceTimeline";

type ViewMode = "rounds" | "timeline";

// ── Decision badge styles ────────────────────────────────────

const DECISION_STYLES: Record<string, string> = {
  continue: "bg-blue-50 text-blue-700",
  converged: "bg-emerald-50 text-emerald-700",
  terminate: "bg-red-50 text-red-700",
};

// ── Round Card ───────────────────────────────────────────────

function RoundCard({
  round,
  generationTraces,
}: {
  round: CreativeRound;
  generationTraces: CreativeTrace[];
}) {
  const decisionStyle =
    DECISION_STYLES[round.round_decision ?? ""] ?? "bg-zinc-50 text-zinc-600";

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-5">
      {/* Round header */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-semibold text-zinc-800">
            Round {round.round_number}
          </h4>
          {round.round_decision && (
            <span
              className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${decisionStyle}`}
            >
              {round.round_decision}
            </span>
          )}
        </div>
        {round.best_agent_role && (
          <span className="flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
            <Trophy className="h-3 w-3" />
            {round.best_agent_role}
            {round.best_score !== null && ` (${round.best_score.toFixed(1)})`}
          </span>
        )}
      </div>

      {/* Agent generation cards */}
      {generationTraces.length > 0 && (
        <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-2">
          {generationTraces.map((trace) => (
            <div
              key={trace.id}
              className="rounded-lg border border-zinc-100 bg-zinc-50 p-3"
            >
              <div className="mb-1 flex items-center justify-between">
                <span className="text-xs font-medium text-zinc-700">
                  {trace.agent_role}
                </span>
                {trace.score !== null && (
                  <span className="rounded bg-white px-1.5 py-0.5 text-[10px] font-semibold text-zinc-600">
                    {trace.score.toFixed(1)}
                  </span>
                )}
              </div>
              <p className="line-clamp-4 text-xs text-zinc-500">
                {trace.output_content}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Leader summary */}
      {round.leader_summary && (
        <div className="flex items-start gap-2 rounded-lg bg-zinc-50 p-3">
          <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-400" />
          <p className="text-xs text-zinc-600">{round.leader_summary}</p>
        </div>
      )}
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────

export default function CreativeRoundView({
  sessionId,
}: {
  sessionId: number;
}) {
  const [timeline, setTimeline] = useState<CreativeTimeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("rounds");

  const fetchTimeline = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get<CreativeTimeline>(
        `${API_BASE}/lab/creative/sessions/${sessionId}/timeline`
      );
      setTimeline(res.data);
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.detail ?? err.message
        : "Failed to load timeline";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);

  if (loading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-xs text-red-600">
        {error}
      </div>
    );
  }

  if (!timeline || timeline.rounds.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-xs text-zinc-400">
        No rounds yet
      </div>
    );
  }

  const tracesByRound = new Map<number, CreativeTrace[]>();
  for (const t of timeline.traces) {
    const list = tracesByRound.get(t.round_number) ?? [];
    list.push(t);
    tracesByRound.set(t.round_number, list);
  }

  return (
    <div className="space-y-4">
      {/* View mode toggle */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setViewMode("rounds")}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
            viewMode === "rounds"
              ? "bg-zinc-900 text-white"
              : "border border-zinc-200 text-zinc-600 hover:bg-zinc-50"
          }`}
        >
          Rounds
        </button>
        <button
          onClick={() => setViewMode("timeline")}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
            viewMode === "timeline"
              ? "bg-zinc-900 text-white"
              : "border border-zinc-200 text-zinc-600 hover:bg-zinc-50"
          }`}
        >
          Full Timeline
        </button>
      </div>

      {viewMode === "rounds" ? (
        <div className="space-y-4">
          {timeline.rounds.map((round) => {
            const roundTraces = tracesByRound.get(round.round_number) ?? [];
            const generationTraces = roundTraces.filter(
              (t) => t.trace_type === "generation"
            );
            return (
              <RoundCard
                key={round.id}
                round={round}
                generationTraces={generationTraces}
              />
            );
          })}
        </div>
      ) : (
        <TraceTimeline traces={timeline.traces} />
      )}
    </div>
  );
}
