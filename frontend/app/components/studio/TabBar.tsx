"use client";

import type { StudioTab } from "../../store/slices/metaSlice";
import { useStudioStore } from "../../store/useStudioStore";
import { getAvatarInitial } from "../../utils";
import { getCurrentProject, getChannelAvatarUrl } from "../../store/selectors/projectSelectors";

const TABS: { id: StudioTab; label: string }[] = [
  { id: "plan", label: "Plan" },
  { id: "scenes", label: "Scenes" },
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
  const currentProject = getCurrentProject();
  const avatarUrl = getChannelAvatarUrl();

  const getBadge = (tab: StudioTab): string | null => {
    if (tab === "scenes" && scenes.length > 0) return String(scenes.length);
    if (tab === "output" && videoUrl) return "1";
    return null;
  };

  return (
    <div className="mx-auto max-w-5xl px-6 pt-3">
      <div className="flex items-center gap-3">
        {/* Tab Navigation */}
        <div className="flex-1 flex gap-1 rounded-xl bg-zinc-100/60 p-1">
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

        {/* Project Info */}
        {currentProject && (
          <div className="flex items-center gap-2 rounded-xl bg-white border border-zinc-200 px-3 py-2">
            <div className="flex h-6 w-6 items-center justify-center overflow-hidden rounded-full border border-zinc-200 bg-zinc-100 text-[10px] font-semibold text-zinc-600">
              {avatarUrl ? (
                <img src={avatarUrl} alt="Avatar" className="h-full w-full object-cover" />
              ) : (
                getAvatarInitial(currentProject.name)
              )}
            </div>
            <span className="text-xs font-medium text-zinc-700 max-w-[100px] truncate">
              {currentProject.name}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
