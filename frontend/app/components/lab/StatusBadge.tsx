"use client";

import { Loader2, CheckCircle, XCircle, Clock } from "lucide-react";

const STATUS_STYLES: Record<
  string,
  { bg: string; text: string; icon: typeof CheckCircle }
> = {
  completed: { bg: "bg-emerald-50", text: "text-emerald-700", icon: CheckCircle },
  running: { bg: "bg-blue-50", text: "text-blue-700", icon: Loader2 },
  failed: { bg: "bg-red-50", text: "text-red-700", icon: XCircle },
  pending: { bg: "bg-zinc-100", text: "text-zinc-600", icon: Clock },
};

export default function StatusBadge({ status }: { status: string }) {
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
