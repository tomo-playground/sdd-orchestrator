"use client";

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
      <div className="flex flex-1 gap-2 overflow-x-auto py-2">
        {scenes.map((s, idx) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onSceneSelect(idx)}
            className={`relative flex-shrink-0 overflow-hidden rounded-xl border-2 transition ${
              idx === currentSceneIndex
                ? "border-zinc-900 shadow-md"
                : "border-zinc-200 opacity-60 hover:opacity-100"
            }`}
            style={{ width: 64, height: 64 }}
          >
            {s.image_url ? (
              <img
                src={s.image_url}
                alt={`Scene ${s.id}`}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-zinc-100 text-[10px] text-zinc-400">
                {s.id}
              </div>
            )}
            <span className="absolute bottom-0 left-0 right-0 bg-black/50 py-0.5 text-center text-[9px] text-white">
              Scene {s.id}
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
      <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500">
        {currentSceneIndex + 1} / {scenes.length}
      </span>
    </div>
  );
}
