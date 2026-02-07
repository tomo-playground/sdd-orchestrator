"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { Loader2, Trophy, MessageSquare, Compass } from "lucide-react";
import { API_BASE } from "../../constants";
import type {
  CreativeRound,
  CreativeSession,
  CreativeTrace,
  CreativeTimeline,
} from "../../types/creative";
import TraceTimeline from "./TraceTimeline";

type ViewMode = "rounds" | "timeline";

// -- Decision badge styles ------------------------------------------------

const DECISION_STYLES: Record<string, string> = {
  continue: "bg-blue-50 text-blue-700",
  converged: "bg-emerald-50 text-emerald-700",
  terminate: "bg-red-50 text-red-700",
};

// -- Agent Compare Panel --------------------------------------------------

function AgentComparePanel({
  traces,
  isLastRound,
  selectedAgentRole,
  onSelect,
}: {
  traces: CreativeTrace[];
  isLastRound: boolean;
  selectedAgentRole?: string;
  onSelect?: (trace: CreativeTrace) => void;
}) {
  const [activeTab, setActiveTab] = useState(0);
  const active = traces[activeTab];
  if (!active) return null;

  return (
    <div className="mb-3">
      {/* Agent tabs */}
      <div className="mb-3 flex gap-1 border-b border-zinc-100 pb-2">
        {traces.map((trace, i) => {
          const isSelected = trace.agent_role === selectedAgentRole;
          return (
            <button
              key={trace.id}
              onClick={() => setActiveTab(i)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                i === activeTab
                  ? "bg-zinc-900 text-white"
                  : isSelected
                    ? "border border-emerald-300 bg-emerald-50 text-emerald-700"
                    : "border border-zinc-200 text-zinc-600 hover:bg-zinc-50"
              }`}
            >
              {isSelected && <Trophy className="h-3 w-3" />}
              {trace.agent_role}
              {trace.score !== null && (
                <span
                  className={`ml-1 text-[10px] ${i === activeTab ? "text-zinc-300" : "text-zinc-400"}`}
                >
                  {trace.score.toFixed(1)}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Active agent output */}
      <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-zinc-700">{active.agent_role}</span>
          <div className="flex items-center gap-2">
            {active.score !== null && (
              <span className="rounded bg-white px-2 py-0.5 text-xs font-semibold text-zinc-600">
                Score: {active.score.toFixed(2)}
              </span>
            )}
            {isLastRound && onSelect && (
              <button
                onClick={() => onSelect(active)}
                className={`rounded-lg px-3 py-1 text-xs font-medium transition ${
                  active.agent_role === selectedAgentRole
                    ? "cursor-default bg-emerald-100 text-emerald-700"
                    : "bg-zinc-900 text-white hover:bg-zinc-700"
                }`}
                disabled={active.agent_role === selectedAgentRole}
              >
                {active.agent_role === selectedAgentRole ? "Selected" : "Select as Final"}
              </button>
            )}
          </div>
        </div>
        <div className="max-h-80 overflow-y-auto">
          <pre className="text-xs leading-relaxed whitespace-pre-wrap text-zinc-600">
            {active.output_content}
          </pre>
        </div>
      </div>
    </div>
  );
}

// -- Round Card -----------------------------------------------------------

function RoundCard({
  round,
  generationTraces,
  isLastRound,
  selectedAgentRole,
  onSelect,
}: {
  round: CreativeRound;
  generationTraces: CreativeTrace[];
  isLastRound: boolean;
  selectedAgentRole?: string;
  onSelect?: (trace: CreativeTrace) => void;
}) {
  const decisionStyle = DECISION_STYLES[round.round_decision ?? ""] ?? "bg-zinc-50 text-zinc-600";

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-5">
      {/* Round header */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h4 className="text-sm font-semibold text-zinc-800">Round {round.round_number}</h4>
          {round.round_decision && (
            <span
              className={`rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-wider uppercase ${decisionStyle}`}
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

      {/* Agent generation compare panel */}
      {generationTraces.length > 0 && (
        <AgentComparePanel
          traces={generationTraces}
          isLastRound={isLastRound}
          selectedAgentRole={selectedAgentRole}
          onSelect={onSelect}
        />
      )}

      {/* Leader summary */}
      {round.leader_summary && (
        <div className="flex items-start gap-2 rounded-lg bg-zinc-50 p-3">
          <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-400" />
          <p className="text-xs text-zinc-600">{round.leader_summary}</p>
        </div>
      )}

      {/* Leader direction */}
      {round.leader_direction && (
        <div className="mt-2 flex items-start gap-2 rounded-lg bg-blue-50 p-3">
          <Compass className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-400" />
          <p className="text-xs text-blue-700">{round.leader_direction}</p>
        </div>
      )}
    </div>
  );
}

// -- Main Component -------------------------------------------------------

export default function CreativeRoundView({
  sessionId,
  session,
  onFinalize,
}: {
  sessionId: number;
  session?: CreativeSession;
  onFinalize?: (trace: CreativeTrace) => void;
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
        ? (err.response?.data?.detail ?? err.message)
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

  const lastRoundNumber = Math.max(...timeline.rounds.map((r) => r.round_number));
  const selectedAgentRole = (session?.final_output as Record<string, unknown> | null)
    ?.agent_role as string | undefined;

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
            const generationTraces = roundTraces.filter((t) => t.trace_type === "generation");
            return (
              <RoundCard
                key={round.id}
                round={round}
                generationTraces={generationTraces}
                isLastRound={round.round_number === lastRoundNumber}
                selectedAgentRole={selectedAgentRole}
                onSelect={onFinalize}
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
