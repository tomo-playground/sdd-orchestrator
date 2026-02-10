"use client";

import { Loader2, CheckCircle, XCircle, Clock, Pause, MessageCircle } from "lucide-react";

const STATUS_STYLES: Record<string, { bg: string; text: string; icon: typeof CheckCircle }> = {
  completed: { bg: "bg-emerald-50", text: "text-emerald-700", icon: CheckCircle },
  running: { bg: "bg-blue-50", text: "text-blue-700", icon: Loader2 },
  failed: { bg: "bg-red-50", text: "text-red-700", icon: XCircle },
  pending: { bg: "bg-zinc-100", text: "text-zinc-600", icon: Clock },
  created: { bg: "bg-zinc-100", text: "text-zinc-600", icon: Clock },
  // V2 statuses
  phase1_running: { bg: "bg-blue-50", text: "text-blue-700", icon: Loader2 },
  phase1_done: { bg: "bg-amber-50", text: "text-amber-700", icon: Pause },
  phase2_running: { bg: "bg-indigo-50", text: "text-indigo-700", icon: Loader2 },
  step_review: { bg: "bg-amber-50", text: "text-amber-700", icon: MessageCircle },
};

const SPINNING = new Set(["running", "phase1_running", "phase2_running"]);

const STATUS_LABELS: Record<string, string> = {
  phase1_running: "Debate",
  phase1_done: "Select",
  phase2_running: "Pipeline",
  step_review: "Review",
};

export default function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  const Icon = style.icon;
  const label = STATUS_LABELS[status] ?? status;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-wider uppercase ${style.bg} ${style.text}`}
    >
      <Icon className={`h-3 w-3 ${SPINNING.has(status) ? "animate-spin" : ""}`} />
      {label}
    </span>
  );
}
