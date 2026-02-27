"use client";

import { Sparkles, Check, X, ArrowRight } from "lucide-react";
import type { CastingRecommendation, Character } from "../../types";

type Props = {
  casting: CastingRecommendation;
  currentChar: Character | null;
  onAccept: () => void;
  onDismiss: () => void;
};

export default function StageCastingCompareCard({
  casting,
  currentChar,
  onAccept,
  onDismiss,
}: Props) {
  return (
    <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-amber-500" />
        <span className="text-sm font-semibold text-amber-900">AI 캐스팅 추천</span>
      </div>

      {/* Compare row */}
      <div className="mb-3 flex items-center gap-3">
        <div className="flex-1 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-center">
          <p className="text-[11px] text-zinc-400">현재</p>
          <p className="text-sm font-medium text-zinc-700">{currentChar?.name ?? "미선택"}</p>
        </div>
        <ArrowRight className="h-4 w-4 shrink-0 text-amber-400" />
        <div className="flex-1 rounded-lg border border-amber-300 bg-amber-100/60 px-3 py-2 text-center">
          <p className="text-[11px] text-amber-500">추천</p>
          <p className="text-sm font-medium text-amber-800">
            {casting.character_name}
            {casting.character_b_name ? ` & ${casting.character_b_name}` : ""}
          </p>
          {casting.structure && (
            <p className="mt-0.5 text-[11px] text-amber-600">{casting.structure}</p>
          )}
        </div>
      </div>

      {/* Reasoning */}
      {casting.reasoning && (
        <p className="mb-3 text-xs leading-relaxed text-amber-700">{casting.reasoning}</p>
      )}

      {/* CTA */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onAccept}
          className="flex items-center gap-1 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-amber-700"
        >
          <Check className="h-3 w-3" />
          수락
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="flex items-center gap-1 rounded-lg border border-amber-300 px-3 py-1.5 text-xs font-medium text-amber-700 transition hover:bg-amber-100"
        >
          <X className="h-3 w-3" />
          무시
        </button>
      </div>
    </div>
  );
}
