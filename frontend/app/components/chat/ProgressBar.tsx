"use client";

import { Loader2 } from "lucide-react";

type Props = {
  progress: { node: string; label: string; percent: number };
};

const NODE_LABEL_MAP: Record<string, string> = {
  director: "디렉터 분석 중",
  director_plan: "기획 수립 중",
  director_checkpoint: "디렉터 검토 중",
  director_plan_gate: "플랜 검토 중",
  writer: "대본 작성 중",
  critic: "품질 검토 중",
  cinematographer: "촬영 설정 중",
  research: "리서치 중",
  concept_gate: "컨셉 생성 중",
  review_gate: "검토 준비 중",
  bgm_selector: "BGM 선택 중",
  image_analysis: "이미지 분석 중",
};

function resolveLabel(node: string, rawLabel: string): string {
  if (NODE_LABEL_MAP[node]) return NODE_LABEL_MAP[node];
  if (NODE_LABEL_MAP[rawLabel]) return NODE_LABEL_MAP[rawLabel];
  // If rawLabel looks like a node name (underscores, no spaces), don't show it raw
  if (rawLabel && !rawLabel.includes(" ") && rawLabel.includes("_")) {
    return "처리 중";
  }
  return rawLabel || "처리 중...";
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
