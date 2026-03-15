"use client";

import { Loader2 } from "lucide-react";

type Props = {
  progress: { node: string; label: string; percent: number };
};

/** Fallback: Backend label이 없는 Frontend 전용 상태용 */
const NODE_LABEL_FALLBACK: Record<string, string> = {
  connecting: "연결 중",
  review_gate: "검토 준비 중",
  image_analysis: "이미지 분석 중",
};

/** "중" / "완료" 등 이미 상태를 나타내는 접미사 목록 */
const STATUS_SUFFIXES = ["중", "완료"];

/** Backend rawLabel에 진행형 접미사 "중"을 붙여 반환 */
function appendProgressSuffix(label: string): string {
  if (STATUS_SUFFIXES.some((s) => label.endsWith(s))) return label;
  return `${label} 중`;
}

function resolveLabel(node: string, rawLabel: string): string {
  // 1) Backend label 우선 (SSOT)
  if (rawLabel && rawLabel.trim()) {
    const trimmed = rawLabel.trim();
    // node name 형태(underscore, 공백 없음)이면 사람용 label 아님 → fallback
    if (!trimmed.includes(" ") && trimmed.includes("_")) {
      return NODE_LABEL_FALLBACK[node] ?? "처리 중";
    }
    return appendProgressSuffix(trimmed);
  }
  // 2) Fallback: Frontend 전용 상태
  if (NODE_LABEL_FALLBACK[node]) return NODE_LABEL_FALLBACK[node];
  return "처리 중";
}

export default function ProgressBar({ progress }: Props) {
  const label = resolveLabel(progress.node, progress.label);

  const pct = Math.round(progress.percent);

  return (
    <div className="w-full bg-transparent px-4 py-2">
      <div className="mx-auto max-w-3xl rounded-2xl border border-zinc-100 bg-white/90 px-4 py-3 shadow-sm backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin text-violet-500" />
          <span className="text-sm font-medium text-zinc-700">{label}</span>
          <span className="ml-auto text-xs font-semibold text-zinc-400">{pct}%</span>
        </div>
        <div
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={label}
          className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-zinc-100"
        >
          <div
            className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-500 transition-all duration-500 ease-out"
            style={{ width: `${Math.min(progress.percent, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
