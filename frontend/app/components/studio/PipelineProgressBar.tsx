"use client";

import { useStudioStore } from "../../store/useStudioStore";

const PIPELINE_STEPS = [
  { id: "script", label: "Script" },
  { id: "images", label: "Images" },
  { id: "render", label: "Render" },
  { id: "video", label: "Video" },
] as const;

export default function PipelineProgressBar() {
  const scenes = useStudioStore((s) => s.scenes);
  const recentVideos = useStudioStore((s) => s.recentVideos);

  const hasScenes = scenes.length > 0;
  const imagesCount = scenes.filter((s) => s.image_url).length;
  const hasAllImages = hasScenes && imagesCount === scenes.length;
  const hasVideos = recentVideos.length > 0;

  const stepStatus = {
    script: hasScenes,
    images: hasAllImages,
    render: hasVideos,
    video: hasVideos,
  };

  const completedCount = Object.values(stepStatus).filter(Boolean).length;
  const percent = Math.round((completedCount / PIPELINE_STEPS.length) * 100);

  return (
    <div className="rounded-xl border border-zinc-200 bg-white px-5 py-3">
      {/* Progress bar */}
      <div className="mb-3 flex items-center gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-zinc-100">
          <div
            className="h-full rounded-full bg-zinc-800 transition-all duration-500"
            style={{ width: `${percent}%` }}
          />
        </div>
        <span className="text-[12px] font-semibold text-zinc-500 tabular-nums">{percent}%</span>
      </div>

      {/* Steps */}
      <div className="flex items-center justify-between">
        {PIPELINE_STEPS.map((step, i) => {
          const done = stepStatus[step.id];
          const inProgress = step.id === "images" && hasScenes && !hasAllImages;

          return (
            <div key={step.id} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-[12px] font-bold ${
                    done
                      ? "bg-zinc-800 text-white"
                      : inProgress
                        ? "border-2 border-zinc-800 text-zinc-800"
                        : "border border-zinc-300 text-zinc-400"
                  }`}
                >
                  {done ? "✓" : inProgress ? `${imagesCount}` : i + 1}
                </div>
                <span
                  className={`mt-1 text-[11px] font-medium ${done ? "text-zinc-700" : "text-zinc-400"}`}
                >
                  {step.label}
                </span>
              </div>
              {i < PIPELINE_STEPS.length - 1 && (
                <div
                  className={`mx-2 mb-4 h-px w-8 ${done ? "bg-zinc-400" : "border-t border-dashed border-zinc-300"}`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
