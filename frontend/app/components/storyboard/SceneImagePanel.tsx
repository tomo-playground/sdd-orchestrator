"use client";

import { useState } from "react";
import { Skeleton } from "../ui";
import type { Scene, ImageValidation, CriticalFailureItem } from "../../types";
import { useSceneContext } from "./SceneContext";

const CRITICAL_FAILURE_LABELS: Record<string, string> = {
  gender_swap: "GENDER SWAP",
  no_subject: "NO CHARACTER",
  count_mismatch: "COUNT MISMATCH",
};

function formatCriticalFailure(f: CriticalFailureItem): string {
  if (f.failure_type === "gender_swap") return `성별 반전: ${f.expected} → ${f.detected}`;
  if (f.failure_type === "no_subject") return `인물 미감지 (expected: ${f.expected})`;
  return `인물수 불일치: ${f.expected}명 → ${f.detected}명`;
}

type SceneImagePanelProps = {
  scene: Scene;
  onImageClick: (imageUrl: string | null) => void;
  onCandidateSelect: (imageUrl: string) => void;
};

function ValidationOverlay({
  result,
  onApplyMissingTags,
}: {
  result?: ImageValidation;
  onApplyMissingTags?: (tags: string[]) => void;
}) {
  if (!result) return null;

  const rate = Math.round((result.match_rate ?? 0) * 100);
  const missingCount = result.missing?.length ?? 0;
  const extraCount = result.extra?.length ?? 0;
  const criticalFailures = result.critical_failure?.failures ?? [];
  const rateColor =
    rate >= 80 ? "text-emerald-400" : rate >= 50 ? "text-amber-400" : "text-red-400";
  const barColor = rate >= 80 ? "bg-emerald-400" : rate >= 50 ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="flex w-full flex-col gap-2 px-4">
      {/* Critical Failure Warning */}
      {criticalFailures.length > 0 && (
        <div className="rounded-lg bg-red-500/80 px-3 py-2 backdrop-blur">
          {criticalFailures.map((f: CriticalFailureItem, i: number) => (
            <p key={i} className="text-[12px] font-bold text-white">
              {formatCriticalFailure(f)}
            </p>
          ))}
        </div>
      )}

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
        {missingCount === 0 && extraCount === 0 && criticalFailures.length === 0 && (
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

      {/* Add Missing Tags action */}
      {missingCount > 0 && onApplyMissingTags && result.missing && (
        <div className="flex gap-2">
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
        </div>
      )}
    </div>
  );
}

export default function SceneImagePanel({
  scene,
  onImageClick,
  onCandidateSelect,
}: SceneImagePanelProps) {
  const { data, callbacks } = useSceneContext();
  const validationResult = data.imageValidationResult;
  const genProgress = data.genProgress;
  const onApplyMissingTags = callbacks.onApplyMissingTags;

  const [hovered, setHovered] = useState(false);
  const [isImageLoading, setIsImageLoading] = useState(true);
  const showOverlay = hovered && scene.image_url && !scene.isGenerating && validationResult;

  return (
    <div className="flex flex-col gap-3">
      <div
        className="group relative aspect-[9/16] w-full max-w-[320px] cursor-pointer overflow-hidden rounded-2xl border border-zinc-200 bg-zinc-50"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={() => scene.image_url && onImageClick(scene.image_url)}
      >
        {/* Generating overlay with SSE progress + preview */}
        {scene.isGenerating && (
          <div className="absolute inset-0 z-[var(--z-dropdown)] flex flex-col items-center justify-center bg-white/90 backdrop-blur-sm">
            {/* Preview image from SD WebUI */}
            {genProgress?.preview_image ? (
              <div className="absolute inset-0">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`data:image/png;base64,${genProgress.preview_image}`}
                  alt="Preview"
                  className="h-full w-full object-cover opacity-60"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-white/80 to-transparent" />
              </div>
            ) : (
              <div className="mb-3 h-10 w-10 animate-spin rounded-full border-4 border-zinc-200 border-t-indigo-500" />
            )}
            {/* Progress info */}
            <div className="relative z-10 flex flex-col items-center gap-2 px-4">
              <p className="text-sm font-semibold text-zinc-700">
                {genProgress?.message || "이미지 생성 중..."}
              </p>
              <div className="h-2 w-40 overflow-hidden rounded-full bg-zinc-200">
                <div
                  className={`h-full rounded-full transition-all duration-500 ease-out ${
                    genProgress
                      ? "bg-indigo-500"
                      : "animate-pulse bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"
                  }`}
                  style={{ width: genProgress ? `${genProgress.percent}%` : "100%" }}
                />
              </div>
              <div className="flex items-center gap-3">
                {genProgress && (
                  <span className="text-[12px] font-bold text-indigo-600">
                    {genProgress.percent}%
                  </span>
                )}
                {genProgress?.estimated_remaining_seconds != null &&
                  genProgress.estimated_remaining_seconds > 0 && (
                    <span className="text-[12px] text-zinc-400">
                      ~{Math.ceil(genProgress.estimated_remaining_seconds)}s 남음
                    </span>
                  )}
              </div>
            </div>
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
              onLoad={() => setIsImageLoading(false)}
              className={`h-full w-full object-contain ${
                isImageLoading ? "opacity-0" : "opacity-100"
              }`}
            />
          </>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3">
            <p className="text-xs text-zinc-400">이미지 없음</p>
            <p className="text-[12px] text-zinc-300">생성 또는 업로드</p>
          </div>
        )}

        {/* Validation overlay on hover */}
        {showOverlay && (
          <div className="absolute inset-0 flex items-end justify-start bg-gradient-to-t from-black/70 via-black/30 to-transparent p-4 transition-opacity">
            <ValidationOverlay result={validationResult} onApplyMissingTags={onApplyMissingTags} />
          </div>
        )}

        {/* Critical failure badge (always visible, top-left) */}
        {!showOverlay && validationResult?.critical_failure?.has_failure && scene.image_url && (
          <div className="absolute top-2 left-2">
            <span className="rounded-full bg-red-600 px-2 py-0.5 text-[11px] font-bold tracking-wider text-white shadow-sm">
              {CRITICAL_FAILURE_LABELS[
                validationResult.critical_failure.failures[0]?.failure_type
              ] ?? "CRITICAL"}
            </span>
          </div>
        )}

        {/* Small match rate badge when not hovered (if validated) */}
        {!showOverlay &&
          validationResult &&
          typeof validationResult.match_rate === "number" &&
          !isNaN(validationResult.match_rate) &&
          scene.image_url && (
            <div className="absolute top-2 right-2">
              <span
                className={`rounded-full px-2 py-0.5 text-[12px] font-bold shadow-sm ${
                  validationResult.match_rate >= 0.8
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
                  className={`group/thumb relative aspect-[9/16] cursor-pointer overflow-hidden rounded-xl border ${
                    isSelected ? "border-zinc-900" : "border-zinc-200"
                  }`}
                  onClick={() => onImageClick(candidate.image_url!)}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={candidate.image_url}
                    alt={`Candidate ${idx + 1}`}
                    loading="lazy"
                    className="h-full w-full object-contain"
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
