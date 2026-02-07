"use client";

import { Loader2, CheckCircle, XCircle, Clock } from "lucide-react";

// ── Types ────────────────────────────────────────────────────

type CreativeSession = {
  id: number;
  task_type: string;
  objective: string;
  status: string;
  created_at: string | null;
};

type Props = {
  sessions: CreativeSession[];
  loading: boolean;
  onSelect: (id: number) => void;
};

// ── Status badge ─────────────────────────────────────────────

const STATUS_STYLES: Record<
  string,
  { bg: string; text: string; icon: typeof CheckCircle }
> = {
  completed: { bg: "bg-emerald-50", text: "text-emerald-700", icon: CheckCircle },
  running: { bg: "bg-blue-50", text: "text-blue-700", icon: Loader2 },
  failed: { bg: "bg-red-50", text: "text-red-700", icon: XCircle },
  pending: { bg: "bg-zinc-100", text: "text-zinc-600", icon: Clock },
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  const Icon = style.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${style.bg} ${style.text}`}
    >
      <Icon
        className={`h-3 w-3 ${status === "running" ? "animate-spin" : ""}`}
      />
      {status}
    </span>
  );
}

// ── Date formatter ───────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Main ─────────────────────────────────────────────────────

export default function SessionHistoryTable({
  sessions,
  loading,
  onSelect,
}: Props) {
  if (sessions.length === 0) {
    return (
      <div className="flex h-24 items-center justify-center rounded-xl border border-dashed border-zinc-300 bg-zinc-50 text-xs text-zinc-400">
        No sessions yet. Start a debate to begin.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white">
      <div className="px-5 pt-4 pb-2">
        <p className="text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
          Session History
        </p>
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="border-b border-zinc-100 px-5 py-2 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
              ID
            </th>
            <th className="border-b border-zinc-100 px-5 py-2 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
              Objective
            </th>
            <th className="border-b border-zinc-100 px-5 py-2 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
              Type
            </th>
            <th className="border-b border-zinc-100 px-5 py-2 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
              Status
            </th>
            <th className="border-b border-zinc-100 px-5 py-2 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
              Created
            </th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr
              key={s.id}
              onClick={() => onSelect(s.id)}
              className="cursor-pointer border-b border-zinc-50 text-zinc-600 transition hover:bg-zinc-50"
            >
              <td className="px-5 py-2.5 font-mono text-[10px]">#{s.id}</td>
              <td className="max-w-xs truncate px-5 py-2.5">{s.objective}</td>
              <td className="px-5 py-2.5">
                <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px]">
                  {s.task_type}
                </span>
              </td>
              <td className="px-5 py-2.5">
                <StatusBadge status={s.status} />
              </td>
              <td className="px-5 py-2.5 text-[10px] text-zinc-400">
                {formatDate(s.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {loading && (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
        </div>
      )}
    </div>
  );
}
