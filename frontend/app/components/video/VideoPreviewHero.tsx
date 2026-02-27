"use client";

import { Film, Loader2, Maximize2 } from "lucide-react";
import type { RenderProgress } from "../../types";
import { STAGE_LABELS } from "./RenderSettingsPanel";

type VideoPreviewHeroProps = {
  videoUrl: string | null;
  onClickFullscreen?: (url: string) => void;
  compact?: boolean;
  isRendering?: boolean;
  renderProgress?: RenderProgress | null;
};

export default function VideoPreviewHero({
  videoUrl,
  onClickFullscreen,
  compact,
  isRendering,
  renderProgress,
}: VideoPreviewHeroProps) {
  /* ── Rendering overlay (no video yet) ── */
  if (isRendering && !videoUrl) {
    return (
      <div className="flex aspect-[9/16] flex-col items-center justify-center gap-4 rounded-2xl border border-zinc-200 bg-zinc-900">
        <Loader2 className="h-8 w-8 animate-spin text-white/70" />
        {renderProgress && (
          <div className="w-4/5 space-y-2">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/20">
              <div
                className="h-full rounded-full bg-white transition-all duration-300 ease-out"
                style={{ width: `${renderProgress.percent}%` }}
              />
            </div>
            <p className="text-center text-xs text-white/60">
              {STAGE_LABELS[renderProgress.stage] || renderProgress.stage}
              {renderProgress.percent > 0 && ` · ${renderProgress.percent}%`}
            </p>
          </div>
        )}
      </div>
    );
  }

  /* ── Empty state ── */
  if (!videoUrl) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-zinc-200 bg-white/70 py-10">
        <Film className="h-10 w-10 text-zinc-300" />
        <p className="text-sm font-medium text-zinc-400">렌더링된 영상 없음</p>
        {!compact && (
          <p className="text-xs text-zinc-400">좌측에서 Render 버튼을 눌러 영상을 생성하세요</p>
        )}
      </div>
    );
  }

  /* ── Video preview ── */
  return (
    <div className={compact ? "relative" : "relative mx-auto max-w-sm"}>
      <div className="aspect-[9/16] overflow-hidden rounded-2xl bg-black shadow-lg">
        <video
          key={videoUrl}
          controls
          playsInline
          preload="metadata"
          src={videoUrl}
          className="h-full w-full object-contain"
        />
      </div>

      {/* Re-rendering overlay on existing video */}
      {isRendering && renderProgress && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-2xl bg-black/60 backdrop-blur-sm">
          <Loader2 className="h-8 w-8 animate-spin text-white/80" />
          <div className="w-3/4 space-y-1.5">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/20">
              <div
                className="h-full rounded-full bg-white transition-all duration-300 ease-out"
                style={{ width: `${renderProgress.percent}%` }}
              />
            </div>
            <p className="text-center text-xs text-white/70">
              {STAGE_LABELS[renderProgress.stage] || renderProgress.stage}
              {renderProgress.percent > 0 && ` · ${renderProgress.percent}%`}
            </p>
          </div>
        </div>
      )}

      {onClickFullscreen && !isRendering && (
        <button
          type="button"
          onClick={() => onClickFullscreen(videoUrl)}
          className="absolute top-2 right-2 rounded-lg bg-black/50 p-1.5 text-white transition hover:bg-black/70"
          title="전체 화면"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
