"use client";

import { useState, useRef } from "react";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useRenderStore } from "../../store/useRenderStore";

const STEPS = [
  { id: "script", label: "대본" },
  { id: "stage", label: "준비" },
  { id: "images", label: "이미지" },
  { id: "render", label: "렌더" },
  { id: "video", label: "영상" },
] as const;

export default function PipelineStatusDots() {
  const scenes = useStoryboardStore((s) => s.scenes);
  const stageStatus = useStoryboardStore((s) => s.stageStatus);
  const recentVideos = useRenderStore((s) => s.recentVideos);
  const isRendering = useRenderStore((s) => s.isRendering);
  const renderProgress = useRenderStore((s) => s.renderProgress);
  const videoUrl = useRenderStore((s) => s.videoUrl);
  const videoUrlFull = useRenderStore((s) => s.videoUrlFull);
  const videoUrlPost = useRenderStore((s) => s.videoUrlPost);

  const [tooltip, setTooltip] = useState<string | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const hasScenes = scenes.length > 0;
  const imagesCount = scenes.filter((s) => s.image_url).length;
  const hasAllImages = hasScenes && imagesCount === scenes.length;
  const hasVideos = recentVideos.length > 0 || !!videoUrl || !!videoUrlFull || !!videoUrlPost;

  const status: Record<string, "done" | "progress" | "error" | "idle"> = {
    script: hasScenes ? "done" : "idle",
    stage:
      stageStatus === "staged"
        ? "done"
        : stageStatus === "staging"
          ? "progress"
          : stageStatus === "failed"
            ? "error"
            : "idle",
    images: hasAllImages ? "done" : hasScenes && imagesCount > 0 ? "progress" : "idle",
    render: hasVideos ? "done" : isRendering ? "progress" : "idle",
    video: hasVideos ? "done" : "idle",
  };

  const renderTooltip = isRendering
    ? `렌더: ${renderProgress ? `${renderProgress.percent}%` : "진행 중"}`
    : hasVideos
      ? "렌더: 완료"
      : "렌더: 미시작";

  const tooltipText: Record<string, string> = {
    script: hasScenes ? `대본: ${scenes.length}개 씬` : "대본: 미시작",
    stage:
      stageStatus === "staged"
        ? "준비: 배경 완료"
        : stageStatus === "staging"
          ? "준비: 생성 중..."
          : stageStatus === "failed"
            ? "준비: 생성 실패"
            : "준비: 미시작",
    images: hasAllImages
      ? `이미지: 전체 ${scenes.length}개 완료`
      : imagesCount > 0
        ? `이미지: ${imagesCount}/${scenes.length}`
        : "이미지: 미시작",
    render: renderTooltip,
    video: hasVideos ? `영상: ${recentVideos.length}개 완료` : "영상: 미시작",
  };

  const showTooltip = (id: string) => {
    clearTimeout(timeoutRef.current);
    setTooltip(tooltipText[id]);
  };

  const hideTooltip = () => {
    timeoutRef.current = setTimeout(() => setTooltip(null), 150);
  };

  return (
    <div className="relative flex items-center gap-1.5">
      {STEPS.map((step) => {
        const s = status[step.id];
        return (
          <div
            key={step.id}
            onMouseEnter={() => showTooltip(step.id)}
            onMouseLeave={hideTooltip}
            className={`h-2 w-2 rounded-full transition-colors ${
              s === "done"
                ? "bg-emerald-500"
                : s === "progress"
                  ? "animate-pulse bg-amber-400"
                  : s === "error"
                    ? "bg-red-500"
                    : "bg-zinc-300"
            }`}
            title={tooltipText[step.id]}
          />
        );
      })}
      {tooltip && (
        <div className="absolute top-full left-1/2 z-10 mt-1.5 -translate-x-1/2 rounded-md bg-zinc-800 px-2 py-1 text-[11px] whitespace-nowrap text-white shadow-lg">
          {tooltip}
        </div>
      )}
    </div>
  );
}
