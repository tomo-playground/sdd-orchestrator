"use client";

import { Trash2 } from "lucide-react";
import Button from "../ui/Button";
import { ERROR_ICON, ERROR_BG } from "../ui/variants";

type SceneNavHeaderProps = {
  currentIndex: number;
  total: number;
  duration?: number;
  onPrev: () => void;
  onNext: () => void;
  onRemove: () => void;
};

export default function SceneNavHeader({
  currentIndex,
  total,
  duration,
  onPrev,
  onNext,
  onRemove,
}: SceneNavHeaderProps) {
  return (
    <div className="flex items-center justify-between border-b border-zinc-200 px-6 py-3">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onPrev}
          disabled={currentIndex === 0}
          aria-label="이전 씬"
          className="flex h-7 w-7 items-center justify-center rounded-full border border-zinc-300 bg-white text-zinc-600 transition hover:bg-zinc-50 disabled:opacity-40"
        >
          &larr;
        </button>
        <span className="text-sm font-medium text-zinc-600 tabular-nums">
          {currentIndex + 1} / {total}
        </span>
        <button
          type="button"
          onClick={onNext}
          disabled={currentIndex >= total - 1}
          aria-label="다음 씬"
          className="flex h-7 w-7 items-center justify-center rounded-full border border-zinc-300 bg-white text-zinc-600 transition hover:bg-zinc-50 disabled:opacity-40"
        >
          &rarr;
        </button>
      </div>
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold text-zinc-800">씬 {currentIndex + 1}</h3>
        {duration != null && <span className="text-xs text-zinc-400">{duration}초</span>}
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onRemove}
          className={`rounded-lg p-2 transition-colors ${ERROR_ICON} hover:${ERROR_BG}`}
          title="Delete Scene"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
}
