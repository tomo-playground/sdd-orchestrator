"use client";

import { useCallback, useEffect } from "react";
import { X } from "lucide-react";
import type { CreativeTimeline } from "../../types/creative";
import TraceTimeline from "./TraceTimeline";

type Props = {
  timeline: CreativeTimeline;
  onClose: () => void;
};

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2 text-center">
      <p className="text-[12px] text-zinc-400">{label}</p>
      <p className="text-sm font-semibold text-zinc-700">{value}</p>
    </div>
  );
}

export default function DebugSlideOver({ timeline, onClose }: Props) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const traces = timeline.traces;
  const totalTokens = traces.reduce((sum, t) => {
    const usage = t.token_usage;
    return sum + (usage?.total_tokens ?? 0);
  }, 0);
  const avgLatency =
    traces.length > 0
      ? Math.round(traces.reduce((sum, t) => sum + t.latency_ms, 0) / traces.length)
      : 0;

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col border-l border-zinc-200 bg-white shadow-xl transition-transform">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-100 px-5 py-3">
        <p className="text-xs font-semibold text-indigo-600">Debug Panel</p>
        <button
          onClick={onClose}
          className="rounded-lg p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 border-b border-zinc-100 px-5 py-3">
        <StatCard label="Traces" value={String(traces.length)} />
        <StatCard label="Total Tokens" value={totalTokens.toLocaleString()} />
        <StatCard label="Avg Latency" value={`${avgLatency}ms`} />
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        <TraceTimeline traces={traces} />
      </div>
    </div>
  );
}
