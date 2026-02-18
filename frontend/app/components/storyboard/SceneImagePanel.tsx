"use client";

import { useState } from "react";
import { Skeleton } from "../ui";
import type { Scene, ImageValidation, ImageGenProgress } from "../../types";

type SceneImagePanelProps = {
  scene: Scene;
  onImageClick: (imageUrl: string | null) => void;
  onCandidateSelect: (imageUrl: string) => void;
  // Generate image callback for empty state CTA
  onGenerateImage?: () => void;
  // Validation overlay
  validationResult?: ImageValidation;
  isValidating?: boolean;
  onValidate?: () => void;
  onApplyMissingTags?: (tags: string[]) => void;
  // SSE progress
  genProgress?: ImageGenProgress | null;
};

function ValidationOverlay({
  result,
  isValidating,
  onValidate,
  onApplyMissingTags,
}: {
  result?: ImageValidation;
  isValidating: boolean;
  onValidate: () => void;
  onApplyMissingTags?: (tags: string[]) => void;
}) {
  if (!result) {
    return (
      <div className="flex flex-col items-center gap-2">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onValidate();
          }}
          disabled={isValidating}
          className="rounded-full bg-white/90 px-4 py-2 text-[12px] font-semibold tracking-[0.15em] uppercase shadow-sm backdrop-blur transition hover:bg-white disabled:opacity-50"
        >
          {isValidating ? "Validating..." : "Run Validation"}
        </button>
      </div>
    );
  }

  const rate = Math.round((result.match_rate ?? 0) * 100);
  const missingCount = result.missing?.length ?? 0;
  const extraCount = result.extra?.length ?? 0;
  const rateColor =
    rate >= 80 ? "text-emerald-400" : rate >= 50 ? "text-amber-400" : "text-red-400";
  const barColor = rate >= 80 ? "bg-emerald-400" : rate >= 50 ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="flex w-full flex-col gap-2 px-4">
      {/* Match Rate */}
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/20">
          <div className={`h-full rounded-full ${barColor}`} style={{ width: `${rate}%` }} />
        </div>
        <span className={`text-lg font-bold ${rateColor}`}>{rate}%</span>
      </div>

      {/* Missing / Extra counts */}
      <div className="flex gap-3 text-[12px] font-semibold tracking-wider">
        {missingCount > 0 && <span className="text-red-300">MISSING {missingCount}</span>}
        {extraCount > 0 && <span className="text-amber-300">EXTRA {extraCount}</span>}
        {missingCount === 0 && extraCount === 0 && (
          <span className="text-emerald-300">PERFECT MATCH</span>
        )}
      </div>

      {/* Missing tags preview */}
      {missingCount > 0 && result.missing && (
        <p className="line-clamp-2 text-[12px] text-white/60">
          {result.missing.slice(0, 5).join(", ")}
          {missingCount > 5 && ` +${missingCount - 5}`}
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onValidate();
          }}
          disabled={isValidating}
          className="rounded-full bg-white/20 px-3 py-1 text-[11px] font-semibold tracking-wider text-white uppercase backdrop-blur transition hover:bg-white/30 disabled:opacity-50"
        >
          {isValidating ? "..." : "Re-validate"}
        </button>
        {missingCount > 0 && onApplyMissingTags && result.missing && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onApplyMissingTags(result.missing!);
            }}
            className="rounded-full bg-red-500/70 px-3 py-1 text-[11px] font-semibold tracking-wider text-white uppercase backdrop-blur transition hover:bg-red-500/90"
          >
            + Add Missing
          </button>
        )}
      </div>
    </div>
  );
}



export default function SceneImagePanel({
  scene,
  onImageClick,
  onCandidateSelect,
  onGenerateImage,
  validationResult,
  isValidating = false,
  onValidate,
  onApplyMissingTags,
  genProgress,
}: SceneImagePanelProps) {
  const [hovered, setHovered] = useState(false);
  const [isImageLoading, setIsImageLoading] = useState(true);
  const showOverlay = hovered && scene.image_url && !scene.isGenerating && onValidate;

  return (
    <div className="flex flex-col gap-3">
      <div
        className="group relative aspect-square w-full max-w-[320px] overflow-hidden rounded-2xl border border-zinc-200 bg-white/70"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* Generating spinner with SSE progress */}
        {scene.isGenerating && (
          <div className="absolute inset-0 z-[var(--z-dropdown)] flex flex-col items-center justify-center gap-3 bg-white/90 backdrop-blur-sm">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-zinc-200 border-t-indigo-500" />
            <p className="text-sm font-semibold text-zinc-700">
              {genProgress?.message || "이미지 생성 중..."}
            </p>
            <div className="h-1.5 w-32 overflow-hidden rounded-full bg-zinc-200">
              <div
                className={`h-full rounded-full transition-all duration-300 ease-out ${genProgress
                  ? "bg-indigo-500"
                  : "animate-pulse bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"
                  }`}
                style={{ width: genProgress ? `${genProgress.percent}%` : "100%" }}
              />
            </div>
            {genProgress && (
              <span className="text-[12px] font-medium text-zinc-500">{genProgress.percent}%</span>
            )}
          </div>
        )}

        {/* Image or placeholder */}
        {scene.image_url ? (
          <>
            {isImageLoading && <Skeleton className="absolute inset-0 h-full w-full bg-zinc-100" />}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={scene.image_url}
              alt={`Scene ${scene.id}`}
              onClick={() => onImageClick(scene.image_url)}
              onLoad={() => setIsImageLoading(false)}
              className={`h-full w-full cursor-pointer object-cover object-top ${isImageLoading ? "opacity-0" : "opacity-100"
                }`}
            />
          </>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3">
            <p className="text-xs text-zinc-400">No image</p>
            <p className="text-[12px] text-zinc-300">Generate or Upload</p>
          </div>
        )}

        {/* Validation overlay on hover */}
        {showOverlay && (
          <div className="absolute inset-0 flex items-end justify-start bg-gradient-to-t from-black/70 via-black/30 to-transparent p-4 transition-opacity">
            <ValidationOverlay
              result={validationResult}
              isValidating={isValidating}
              onValidate={onValidate!}
              onApplyMissingTags={onApplyMissingTags}
            />
          </div>
        )}

        {/* Small badge when not hovered (if validated) */}
        {!showOverlay &&
          validationResult &&
          typeof validationResult.match_rate === "number" &&
          !isNaN(validationResult.match_rate) &&
          scene.image_url && (
            <div className="absolute top-2 right-2">
              <span
                className={`rounded-full px-2 py-0.5 text-[12px] font-bold shadow-sm ${validationResult.match_rate >= 0.8
                  ? "bg-emerald-500 text-white"
                  : validationResult.match_rate >= 0.5
                    ? "bg-amber-500 text-white"
                    : "bg-red-500 text-white"
                  }`}
              >
                {Math.round(validationResult.match_rate * 100)}%
              </span>
            </div>
          )}
      </div>

      {/* Candidates */}
      {scene.candidates && scene.candidates.filter((c) => c.image_url).length > 1 && (
        <div className="grid grid-cols-3 gap-2">
          {scene.candidates
            .filter((c) => c.image_url)
            .map((candidate, idx) => {
              const isSelected = candidate.image_url === scene.image_url;
              return (
                <div
                  key={`${scene.client_id}-candidate-${idx}`}
                  className={`group/thumb relative overflow-hidden rounded-xl border cursor-pointer ${isSelected ? "border-zinc-900" : "border-zinc-200"
                    }`}
                  onClick={() => onImageClick(candidate.image_url!)}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={candidate.image_url}
                    alt={`Candidate ${idx + 1}`}
                    loading="lazy"
                    className="h-full w-full object-cover"
                  />
                  {candidate.match_rate != null && (
                    <span className="absolute top-1 right-1 rounded-full bg-black/60 px-1.5 py-0.5 text-[11px] font-bold text-white">
                      {Math.round(candidate.match_rate * 100)}%
                    </span>
                  )}
                  {/* Select button on hover */}
                  {!isSelected && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onCandidateSelect(candidate.image_url!);
                      }}
                      className="absolute bottom-1 left-1/2 -translate-x-1/2 rounded-full bg-white/90 px-2.5 py-1 text-[11px] font-semibold text-zinc-700 opacity-0 shadow-sm backdrop-blur transition group-hover/thumb:opacity-100"
                    >
                      Use
                    </button>
                  )}
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
