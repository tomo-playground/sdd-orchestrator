"use client";

import { useEffect, useRef } from "react";
import type { Scene } from "../../types";

type SceneFilmstripProps = {
  scenes: Scene[];
  currentSceneIndex: number;
  onSceneSelect: (index: number) => void;
};

export default function SceneFilmstrip({
  scenes,
  currentSceneIndex,
  onSceneSelect,
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
            key={s.id}
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
              <div className="flex h-full w-full items-center justify-center bg-zinc-100 text-[10px] text-zinc-400">
                {idx + 1}
              </div>
            )}
            <span className="absolute right-0 bottom-0 left-0 bg-black/50 py-0.5 text-center text-[9px] text-white">
              Scene {idx + 1}
            </span>
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
      <span className="rounded-md bg-zinc-100 px-2 py-1 text-[10px] font-semibold text-zinc-600 tabular-nums">
        {currentSceneIndex + 1} / {scenes.length}
      </span>
    </div>
  );
}
