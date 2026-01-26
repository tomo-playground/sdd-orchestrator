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
      <div className="aspect-square w-full overflow-hidden rounded-2xl border border-zinc-200 bg-white/70">
        {scene.image_url ? (
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
