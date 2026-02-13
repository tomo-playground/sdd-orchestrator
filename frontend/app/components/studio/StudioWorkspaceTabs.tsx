"use client";

import { useUIStore, type StudioTab } from "../../store/useUIStore";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useRenderStore } from "../../store/useRenderStore";

function useTabBadges(): Record<StudioTab, string | null> {
  const scenesCount = useStoryboardStore((s) => s.scenes.length);
  const recentVideos = useRenderStore((s) => s.recentVideos);
  const renderProgress = useRenderStore((s) => s.renderProgress);

  return {
    edit: scenesCount > 0 ? `${scenesCount}` : null,
    render: renderProgress ? `${renderProgress.percent}%` : null,
    output: recentVideos.length > 0 ? `${recentVideos.length}` : null,
  };
}

const TABS: { key: StudioTab; label: string }[] = [
  { key: "edit", label: "Edit" },
  { key: "render", label: "Render" },
  { key: "output", label: "Output" },
];

export default function StudioWorkspaceTabs() {
  const activeTab = useUIStore((s) => s.activeTab);
  const setActiveTab = useUIStore((s) => s.setActiveTab);
  const badges = useTabBadges();

  return (
    <div className="flex items-center gap-1 rounded-lg bg-zinc-100 p-0.5">
      {TABS.map((tab) => {
        const active = activeTab === tab.key;
        const badge = badges[tab.key];
        return (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold transition ${
              active ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-700"
            }`}
          >
            {tab.label}
            {badge && (
              <span
                className={`rounded-full px-1.5 py-px text-[11px] font-bold leading-tight ${
                  active ? "bg-zinc-100 text-zinc-600" : "bg-zinc-200/80 text-zinc-500"
                }`}
              >
                {badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
