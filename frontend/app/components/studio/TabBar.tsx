"use client";

import type { StudioTab } from "../../store/slices/metaSlice";
import { useStudioStore } from "../../store/useStudioStore";

const TABS: { id: StudioTab; label: string }[] = [
  { id: "plan", label: "Plan" },
  { id: "scenes", label: "Scenes" },
  { id: "render", label: "Render" },
  { id: "output", label: "Video" },
  { id: "insights", label: "Insights" },
];

const STEPS: { label: string; tab: StudioTab }[] = [
  { label: "Plan", tab: "plan" },
  { label: "Scenes", tab: "scenes" },
  { label: "Render", tab: "render" },
  { label: "Video", tab: "output" },
];

interface TabBarProps {
  activeTab: StudioTab;
  onTabChange: (tab: StudioTab) => void;
}

export default function TabBar({ activeTab, onTabChange }: TabBarProps) {
  const scenes = useStudioStore((s) => s.scenes);
  const recentVideos = useStudioStore((s) => s.recentVideos);

  const getBadge = (tab: StudioTab): string | null => {
    if (tab === "scenes" && scenes.length > 0) return String(scenes.length);
    if (tab === "output" && recentVideos.length > 0) return String(recentVideos.length);
    return null;
  };

  const hasImages = scenes.some((s) => s.image_url);
  const hasVideos = recentVideos.length > 0;
  const done = [scenes.length > 0, hasImages, hasVideos, hasVideos];
  const activeIdx = STEPS.findIndex((s) => s.tab === activeTab);

  return (
    <div className="mx-auto w-full max-w-5xl px-6 pt-3">
      <div className="flex gap-1 rounded-xl bg-zinc-100/60 p-1">
        {TABS.map((tab) => {
          const badge = getBadge(tab.id);
          return (
            <button
              key={tab.id}
              data-testid={`tab-${tab.id}`}
              onClick={() => onTabChange(tab.id)}
              className={`relative flex-1 rounded-lg py-2 text-xs font-semibold transition ${
                activeTab === tab.id
                  ? "bg-white text-zinc-900 shadow-sm"
                  : "text-zinc-500 hover:text-zinc-700"
              }`}
            >
              {tab.label}
              {badge && (
                <span className="ml-1 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-zinc-900 px-1 text-[9px] font-bold text-white">
                  {badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
      {activeTab !== "insights" && (
        <div className="flex items-center justify-center gap-0 px-12 pt-1.5 pb-0.5">
          {STEPS.map((step, i) => {
            const isCurrent = i === activeIdx;
            const filled = done[i];
            return (
              <div key={step.tab} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={`h-2 w-2 rounded-full border transition-colors ${
                      isCurrent
                        ? "animate-pulse border-zinc-900 bg-zinc-900"
                        : filled
                          ? "border-zinc-900 bg-zinc-900"
                          : "border-zinc-300 bg-transparent"
                    }`}
                  />
                  <span className="mt-0.5 text-[9px] leading-none text-zinc-400">{step.label}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={`mx-1 mb-3 h-px w-10 ${filled ? "bg-zinc-400" : "border-t border-dashed border-zinc-300 bg-transparent bg-zinc-300"}`}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
