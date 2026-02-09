"use client";

import { useState, useMemo, useCallback } from "react";
import { Clock, Cpu, ChevronDown, ChevronRight, Filter } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { CreativeTrace } from "../../types/creative";

type Props = {
  traces: CreativeTrace[];
};

// ── Trace type style map ─────────────────────────────────────

const TRACE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  instruction: { bg: "bg-blue-50", text: "text-blue-700", label: "Instruction" },
  generation: { bg: "bg-emerald-50", text: "text-emerald-700", label: "Generation" },
  evaluation: { bg: "bg-amber-50", text: "text-amber-700", label: "Evaluation" },
  revision: { bg: "bg-purple-50", text: "text-purple-700", label: "Revision" },
  // V2 trace types
  decision: { bg: "bg-orange-50", text: "text-orange-700", label: "Decision" },
  handoff: { bg: "bg-sky-50", text: "text-sky-700", label: "Handoff" },
  feedback: { bg: "bg-rose-50", text: "text-rose-700", label: "Feedback" },
  quality_report: { bg: "bg-teal-50", text: "text-teal-700", label: "QC Report" },
};

function getTraceStyle(traceType: string) {
  return TRACE_STYLES[traceType] ?? { bg: "bg-zinc-50", text: "text-zinc-700", label: traceType };
}

// ── Helpers ──────────────────────────────────────────────────

function formatLatency(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

function formatTokens(usage: Record<string, number> | null): string {
  if (!usage) return "-";
  const total = usage.total_tokens ?? usage.prompt_tokens + (usage.completion_tokens ?? 0);
  return total ? total.toLocaleString() : "-";
}

// ── Trace Card ───────────────────────────────────────────────

function TraceCard({ trace }: { trace: CreativeTrace }) {
  const [expanded, setExpanded] = useState(false);
  const style = getTraceStyle(trace.trace_type);

  const toggle = useCallback(() => setExpanded((p) => !p), []);

  const contentPreview =
    trace.output_content.length > 200
      ? trace.output_content.slice(0, 200) + "..."
      : trace.output_content;

  return (
    <div className={`rounded-lg border border-zinc-100 ${style.bg} p-3`}>
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-wider uppercase ${style.text}`}
          >
            {style.label}
          </span>
          <span className="text-xs font-medium text-zinc-700">{trace.agent_role}</span>
          {trace.target_agent && (
            <span className="text-[10px] text-zinc-400">→ {trace.target_agent}</span>
          )}
        </div>
        <div className="flex items-center gap-3 text-[10px] text-zinc-400">
          <span className="flex items-center gap-0.5">
            <Cpu className="h-3 w-3" />
            {trace.model_id}
          </span>
          <span className="flex items-center gap-0.5">
            <Clock className="h-3 w-3" />
            {formatLatency(trace.latency_ms)}
          </span>
          <span>{formatTokens(trace.token_usage)} tok</span>
          {trace.score !== null && (
            <span className="rounded bg-white px-1.5 py-0.5 font-semibold text-zinc-600">
              {trace.score.toFixed(1)}
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <button onClick={toggle} className="mt-2 flex w-full items-start gap-1 text-left">
        {expanded ? (
          <ChevronDown className="mt-0.5 h-3 w-3 shrink-0 text-zinc-400" />
        ) : (
          <ChevronRight className="mt-0.5 h-3 w-3 shrink-0 text-zinc-400" />
        )}
        <div className="prose prose-sm prose-zinc max-w-none flex-1 text-xs">
          <ReactMarkdown>{expanded ? trace.output_content : contentPreview}</ReactMarkdown>
        </div>
      </button>

      {/* Feedback row */}
      {trace.feedback && (
        <p className="mt-2 border-t border-zinc-100 pt-2 text-[10px] text-zinc-500">
          <span className="font-semibold">Feedback:</span> {trace.feedback}
        </p>
      )}
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────

export default function TraceTimeline({ traces }: Props) {
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [phaseFilter, setPhaseFilter] = useState<string>("all");

  const agentRoles = useMemo(() => {
    const roles = new Set(traces.map((t) => t.agent_role));
    return Array.from(roles).sort();
  }, [traces]);

  const phases = useMemo(() => {
    const set = new Set(traces.map((t) => t.phase).filter(Boolean));
    return Array.from(set).sort() as string[];
  }, [traces]);

  const filteredTraces = useMemo(() => {
    const sorted = [...traces].sort((a, b) => {
      if (a.round_number !== b.round_number) return a.round_number - b.round_number;
      return a.sequence - b.sequence;
    });
    return sorted.filter((t) => {
      if (roleFilter !== "all" && t.agent_role !== roleFilter) return false;
      if (phaseFilter !== "all" && t.phase !== phaseFilter) return false;
      return true;
    });
  }, [traces, roleFilter, phaseFilter]);

  const groupedByRound = useMemo(() => {
    const groups = new Map<number, CreativeTrace[]>();
    for (const t of filteredTraces) {
      const list = groups.get(t.round_number) ?? [];
      list.push(t);
      groups.set(t.round_number, list);
    }
    return groups;
  }, [filteredTraces]);

  if (traces.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-xs text-zinc-400">
        No traces available
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex items-center gap-2">
        <Filter className="h-3.5 w-3.5 text-zinc-400" />
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
        >
          <option value="all">All Agents</option>
          {agentRoles.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>
        <select
          value={phaseFilter}
          onChange={(e) => setPhaseFilter(e.target.value)}
          className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
        >
          <option value="all">All Phases</option>
          {phases.map((phase) => (
            <option key={phase} value={phase}>
              {phase}
            </option>
          ))}
        </select>
        <span className="text-[10px] text-zinc-400">
          {filteredTraces.length} trace{filteredTraces.length !== 1 && "s"}
        </span>
      </div>

      {/* Rounds */}
      {Array.from(groupedByRound.entries()).map(([roundNum, roundTraces]) => (
        <div key={roundNum}>
          <p className="mb-2 text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Round {roundNum}
          </p>
          <div className="space-y-2">
            {roundTraces.map((trace) => (
              <TraceCard key={trace.id} trace={trace} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
