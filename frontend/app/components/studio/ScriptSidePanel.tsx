"use client";

import { FileText, Sparkles } from "lucide-react";
import { SIDE_PANEL_LABEL } from "../ui/variants";

type Props = {
  scenesCount: number;
  isFull: boolean;
};

const QUICK_TIPS = [
  "첫 3초 안에 시선을 끄는 주제를 작성하세요",
  "30~60초 길이가 참여율에 가장 효과적입니다",
  "캐릭터 중심 스토리에는 Narrated Dialogue를 사용하세요",
  "설명을 추가하면 AI 톤과 스타일을 유도할 수 있습니다",
];

const FULL_TIPS = [
  "AI가 컨셉 토론 후 대본을 생성합니다",
  "검토 결과를 확인한 후 승인하세요",
  "수정 요청 시 피드백을 구체적으로 작성하세요",
  "Preset으로 자동 승인 / 수동 승인을 선택할 수 있습니다",
];

export default function ScriptSidePanel({ scenesCount, isFull }: Props) {
  const tips = isFull ? FULL_TIPS : QUICK_TIPS;

  return (
    <>
      {/* Status */}
      <div>
        <span className={SIDE_PANEL_LABEL}>
          <FileText className="mr-1 inline h-3 w-3" />
          Status
        </span>
        <div className="mt-2 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-500">Mode</span>
            <span className="font-medium text-zinc-700">{isFull ? "Full" : "Quick"}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-500">Scenes</span>
            <span className="font-semibold text-zinc-700">{scenesCount}</span>
          </div>
        </div>
      </div>

      {/* Tips */}
      <div className="border-t border-zinc-100 pt-3">
        <span className={SIDE_PANEL_LABEL}>
          <Sparkles className="mr-1 inline h-3 w-3" />
          Tips
        </span>
        <ul className="mt-2 space-y-1.5">
          {tips.map((tip, i) => (
            <li key={i} className="flex items-start gap-1.5 text-xs text-zinc-600">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-zinc-300" />
              {tip}
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
