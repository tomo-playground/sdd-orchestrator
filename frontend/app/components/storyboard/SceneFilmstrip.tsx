"use client";

import { useEffect, useRef } from "react";
import type { Scene, ImageValidation } from "../../types";
import { hasSceneImage } from "../../utils/sceneCompletion";

type SceneFilmstripProps = {
  scenes: Scene[];
  currentSceneIndex: number;
  onSceneSelect: (index: number) => void;
  imageValidationResults?: Record<string, ImageValidation>;
};

export default function SceneFilmstrip({
  scenes,
  currentSceneIndex,
  onSceneSelect,
  imageValidationResults,
}: SceneFilmstripProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    const el = itemRefs.current[currentSceneIndex];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }
  }, [currentSceneIndex]);

  if (scenes.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={() => onSceneSelect(Math.max(0, currentSceneIndex - 1))}
        disabled={currentSceneIndex === 0}
        className="flex h-8 w-8 items-center justify-center rounded-full border border-zinc-300 bg-white/80 text-zinc-600 disabled:opacity-40"
      >
        ‹
      </button>
      <div ref={scrollRef} className="flex flex-1 gap-2 overflow-x-auto py-2">
        {scenes.map((s, idx) => (
          <button
            key={s.client_id}
            ref={(el) => {
              itemRefs.current[idx] = el;
            }}
            type="button"
            onClick={() => onSceneSelect(idx)}
            className={`relative flex-shrink-0 overflow-hidden rounded-xl border-2 transition-all ${
              idx === currentSceneIndex
                ? "scale-105 border-zinc-900 shadow-md ring-2 ring-zinc-900/20 ring-offset-1"
                : "border-zinc-200 opacity-60 hover:opacity-100"
            }`}
            style={{ width: 64, height: 64 }}
          >
            {s.image_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={s.image_url}
                alt={`Scene ${idx + 1}`}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-zinc-100 text-[12px] text-zinc-400">
                {idx + 1}
              </div>
            )}
            <span className="absolute right-0 bottom-0 left-0 bg-black/50 py-0.5 text-center text-[11px] text-white">
              Scene {idx + 1}
            </span>
            <CompletionDots scene={s} imageValidationResults={imageValidationResults} />
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={() => onSceneSelect(Math.min(scenes.length - 1, currentSceneIndex + 1))}
        disabled={currentSceneIndex === scenes.length - 1}
        className="flex h-8 w-8 items-center justify-center rounded-full border border-zinc-300 bg-white/80 text-zinc-600 disabled:opacity-40"
      >
        ›
      </button>
      <span className="rounded-md bg-zinc-100 px-2 py-1 text-[12px] font-semibold text-zinc-600 tabular-nums">
        {currentSceneIndex + 1} / {scenes.length}
      </span>
    </div>
  );
}

/* ---- Completion Dots ---- */

const DOT_COLORS = {
  green: "bg-emerald-400",
  amber: "bg-amber-400",
  red: "bg-rose-400",
  gray: "bg-zinc-300",
} as const;

function CompletionDots({
  scene,
  imageValidationResults,
}: {
  scene: Scene;
  imageValidationResults?: Record<string, ImageValidation>;
}) {
  const hasScript = scene.script.trim().length > 0;
  const hasImage = hasSceneImage(scene);
  const matchResult = imageValidationResults?.[scene.client_id];
  const rate = matchResult?.match_rate;
  const hasActions = (scene.character_actions?.length ?? 0) > 0;

  const scriptColor = hasScript ? "green" : "red";
  const imageColor = hasImage ? "green" : "red";
  const validationColor =
    rate == null ? "gray" : rate >= 70 ? "green" : rate >= 50 ? "amber" : "red";
  const actionColor = hasActions ? "green" : "gray";

  const dots: Array<{ color: keyof typeof DOT_COLORS; label: string }> = [
    { color: scriptColor, label: `대본: ${hasScript ? "있음" : "없음"}` },
    { color: imageColor, label: `이미지: ${hasImage ? "있음" : "없음"}` },
    {
      color: validationColor,
      label: rate != null ? `검증: ${Math.round(rate)}%` : "검증: 미실행",
    },
    { color: actionColor, label: `액션: ${hasActions ? "있음" : "N/A"}` },
  ];

  return (
    <div className="absolute top-0.5 right-0 left-0 flex justify-center gap-0.5">
      {dots.map((d) => (
        <span
          key={d.label}
          title={d.label}
          className={`h-1.5 w-1.5 rounded-full ${DOT_COLORS[d.color]} ring-1 ring-black/20`}
        />
      ))}
    </div>
  );
}
