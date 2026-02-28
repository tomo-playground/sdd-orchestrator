"use client";

import type { ImageGenProgress } from "../../types";

type GenProgressOverlayProps = {
  genProgress?: ImageGenProgress | null;
};

export default function GenProgressOverlay({ genProgress }: GenProgressOverlayProps) {
  return (
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
            <span className="text-[12px] font-bold text-indigo-600">{genProgress.percent}%</span>
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
  );
}
