"use client";

import type { Scene } from "../../types";

type SceneImagePanelProps = {
  scene: Scene;
  onImageClick: (imageUrl: string | null) => void;
  onCandidateSelect: (imageUrl: string) => void;
};

export default function SceneImagePanel({
  scene,
  onImageClick,
  onCandidateSelect,
}: SceneImagePanelProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="relative aspect-square w-full overflow-hidden rounded-2xl border border-zinc-200 bg-white/70">
        {scene.isGenerating && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-white/90 backdrop-blur-sm">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-zinc-200 border-t-indigo-500"></div>
            <p className="text-sm font-semibold text-zinc-700">이미지 생성 중...</p>
            <div className="h-1 w-32 overflow-hidden rounded-full bg-zinc-200">
              <div className="h-full animate-pulse bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" style={{ width: '100%' }}></div>
            </div>
          </div>
        )}
        {scene.image_url ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={scene.image_url}
            alt={`Scene ${scene.id}`}
            onClick={() => onImageClick(scene.image_url)}
            className="h-full w-full cursor-pointer object-cover object-top"
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2">
            <p className="text-xs text-zinc-400">No image</p>
            <p className="text-[10px] text-zinc-300">Click Generate or Upload</p>
          </div>
        )}
      </div>
      {scene.candidates && scene.candidates.length > 1 && (
        <div className="grid grid-cols-3 gap-2">
          {scene.candidates.map((candidate, idx) => {
            const isSelected = candidate.image_url === scene.image_url;
            return (
              <button
                key={`${scene.id}-candidate-${idx}`}
                type="button"
                onClick={() => onCandidateSelect(candidate.image_url)}
                className={`overflow-hidden rounded-xl border ${
                  isSelected ? "border-zinc-900" : "border-zinc-200"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={candidate.image_url}
                  alt={`Candidate ${idx + 1}`}
                  loading="lazy"
                  className="h-full w-full object-cover"
                />
              </button>
            );
          })}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2 text-[10px] tracking-[0.2em] text-zinc-400 uppercase">
        <span>{scene.image_url ? "Ready" : "Upload required"}</span>
        <span className="rounded-full border border-zinc-200 bg-white/80 px-2 py-0.5 text-[9px] text-zinc-500">
          512x768
        </span>
        <span className="rounded-full border border-zinc-200 bg-white/80 px-2 py-0.5 text-[9px] text-zinc-500">
          Steps {scene.steps}
        </span>
        <span className="rounded-full border border-zinc-200 bg-white/80 px-2 py-0.5 text-[9px] text-zinc-500">
          Seed {scene.seed}
        </span>
      </div>
    </div>
  );
}
