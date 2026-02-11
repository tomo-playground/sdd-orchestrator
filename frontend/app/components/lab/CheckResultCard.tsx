"use client";

import { CheckCircle, AlertTriangle, XCircle } from "lucide-react";
import type { CopyrightResult } from "../../types/creative";

type Props = {
  result: CopyrightResult;
};

const STATUS_STYLES = {
  PASS: {
    icon: CheckCircle,
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    text: "text-emerald-700",
  },
  WARN: {
    icon: AlertTriangle,
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-700",
  },
  FAIL: { icon: XCircle, bg: "bg-red-50", border: "border-red-200", text: "text-red-700" },
};

export default function CheckResultCard({ result }: Props) {
  const overall = STATUS_STYLES[result.overall] ?? STATUS_STYLES.PASS;
  const OverallIcon = overall.icon;

  return (
    <div className={`rounded-xl border ${overall.border} ${overall.bg} p-4`}>
      <div className="mb-2 flex items-center gap-2">
        <OverallIcon className={`h-4 w-4 ${overall.text}`} />
        <span className={`text-xs font-semibold ${overall.text}`}>
          Copyright Review: {result.overall}
        </span>
        <span className="text-[12px] text-zinc-400">
          confidence: {(result.confidence * 100).toFixed(0)}%
        </span>
      </div>

      <div className="space-y-1">
        {result.checks.map((check) => {
          const s = STATUS_STYLES[check.status] ?? STATUS_STYLES.PASS;
          const Icon = s.icon;
          return (
            <div key={check.type} className="flex items-start gap-2">
              <Icon className={`mt-0.5 h-3 w-3 shrink-0 ${s.text}`} />
              <div>
                <span className="text-[12px] font-semibold text-zinc-600">{check.type}</span>
                {check.detail && <p className="text-[12px] text-zinc-500">{check.detail}</p>}
                {check.suggestion && (
                  <p className="text-[12px] text-blue-500">Suggestion: {check.suggestion}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
