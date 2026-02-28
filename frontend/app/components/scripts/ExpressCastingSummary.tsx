"use client";

import { Sparkles, ArrowRight } from "lucide-react";
import type { CastingRecommendation } from "../../types";

type Props = {
  casting: CastingRecommendation;
  onGoToStage: () => void;
};

export default function ExpressCastingSummary({ casting, onGoToStage }: Props) {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4">
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-amber-500" />
        <h3 className="text-sm font-semibold text-amber-900">AI 캐스팅 결정</h3>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
        <div>
          <span className="text-amber-600">캐릭터</span>
          <span className="ml-2 font-medium text-amber-900">
            {casting.character_name || "미정"}
            {casting.character_b_name ? ` & ${casting.character_b_name}` : ""}
          </span>
        </div>
        <div>
          <span className="text-amber-600">구조</span>
          <span className="ml-2 font-medium text-amber-900">{casting.structure || "미정"}</span>
        </div>
      </div>

      {casting.reasoning && (
        <p className="mt-2 text-xs leading-relaxed text-amber-700">{casting.reasoning}</p>
      )}

      <button
        type="button"
        onClick={onGoToStage}
        className="mt-3 flex items-center gap-1 text-xs font-medium text-amber-700 transition hover:text-amber-900"
      >
        Stage에서 변경
        <ArrowRight className="h-3 w-3" />
      </button>
    </div>
  );
}
