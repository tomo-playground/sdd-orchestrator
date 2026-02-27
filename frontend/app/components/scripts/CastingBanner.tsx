"use client";

import { Sparkles, Check, X } from "lucide-react";
import type { CastingRecommendation } from "../../types";

type Props = {
  casting: CastingRecommendation;
  onAccept: () => void;
  onDismiss: () => void;
};

export default function CastingBanner({ casting, onAccept, onDismiss }: Props) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
      <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-amber-900">
          AI 캐스팅 추천: {casting.character_name}
          {casting.character_b_name ? ` & ${casting.character_b_name}` : ""}
          {casting.structure && (
            <span className="ml-1.5 text-xs font-normal text-amber-600">({casting.structure})</span>
          )}
        </p>
        {casting.reasoning && (
          <p className="mt-1 text-xs leading-relaxed text-amber-700">{casting.reasoning}</p>
        )}
      </div>
      <div className="flex shrink-0 gap-1.5">
        <button
          type="button"
          onClick={onAccept}
          className="flex items-center gap-1 rounded-lg bg-amber-600 px-2.5 py-1 text-xs font-medium text-white transition hover:bg-amber-700"
        >
          <Check className="h-3 w-3" />
          수락
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="flex items-center gap-1 rounded-lg border border-amber-300 px-2.5 py-1 text-xs font-medium text-amber-700 transition hover:bg-amber-100"
        >
          <X className="h-3 w-3" />
          무시
        </button>
      </div>
    </div>
  );
}
