"use client";

import type { StudioTab } from "../../store/slices/metaSlice";
import { useStudioStore } from "../../store/useStudioStore";

const TABS: { id: StudioTab; label: string }[] = [
  { id: "plan", label: "Plan" },
  { id: "scenes", label: "Scenes" },
  { id: "render", label: "Render" },
  { id: "output", label: "Output" },
  { id: "insights", label: "Insights" },
];

interface TabBarProps {
  activeTab: StudioTab;
  onTabChange: (tab: StudioTab) => void;
}

export default function TabBar({ activeTab, onTabChange }: TabBarProps) {
  const scenes = useStudioStore((s) => s.scenes);
  const videoUrl = useStudioStore((s) => s.videoUrl);

  const getBadge = (tab: StudioTab): string | null => {
    if (tab === "scenes" && scenes.length > 0) return String(scenes.length);
    if (tab === "render" && videoUrl) return "1";
    return null;
  };

  return (
    <div className="mx-auto max-w-5xl px-6 pt-3">
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
    </div>
  );
}
