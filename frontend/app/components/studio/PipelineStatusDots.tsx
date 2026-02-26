"use client";

import { useState, useRef } from "react";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useRenderStore } from "../../store/useRenderStore";

const STEPS = [
  { id: "script", label: "Script" },
  { id: "stage", label: "Stage" },
  { id: "images", label: "Images" },
  { id: "render", label: "Render" },
  { id: "video", label: "Video" },
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
    ? `Render: ${renderProgress ? `${renderProgress.percent}%` : "in progress"}`
    : hasVideos
      ? "Render: complete"
      : "Render: not started";

  const tooltipText: Record<string, string> = {
    script: hasScenes ? `Script: ${scenes.length} scenes` : "Script: not started",
    stage:
      stageStatus === "staged"
        ? "Stage: backgrounds ready"
        : stageStatus === "staging"
          ? "Stage: generating..."
          : stageStatus === "failed"
            ? "Stage: generation failed"
            : "Stage: not started",
    images: hasAllImages
      ? `Images: all ${scenes.length} done`
      : imagesCount > 0
        ? `Images: ${imagesCount}/${scenes.length}`
        : "Images: not started",
    render: renderTooltip,
    video: hasVideos ? `Video: ${recentVideos.length} rendered` : "Video: not started",
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
