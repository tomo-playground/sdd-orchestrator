"use client";

import type { StudioTab } from "../../store/slices/metaSlice";
import { useStudioStore } from "../../store/useStudioStore";
import { getAvatarInitial } from "../../utils";

const TABS: { id: StudioTab; label: string }[] = [
  { id: "plan", label: "Plan" },
  { id: "scenes", label: "Scenes" },
  { id: "output", label: "Output" },
  { id: "insights", label: "Insights" },
];

interface TabBarProps {
  activeTab: StudioTab;
  onTabChange: (tab: StudioTab) => void;
  onOpenChannelProfile: () => void;
}

export default function TabBar({ activeTab, onTabChange, onOpenChannelProfile }: TabBarProps) {
  const scenes = useStudioStore((s) => s.scenes);
  const videoUrl = useStudioStore((s) => s.videoUrl);
  const channelProfile = useStudioStore((s) => s.channelProfile);
  const channelAvatarUrl = useStudioStore((s) => s.channelAvatarUrl);

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

        {/* Channel Profile Button */}
        <button
          onClick={onOpenChannelProfile}
          data-testid="channel-profile-btn"
          className="flex items-center gap-2 rounded-xl bg-white border border-zinc-200 px-3 py-2 hover:bg-zinc-50 transition-colors"
        >
          {channelProfile ? (
            <>
              <div className="flex h-6 w-6 items-center justify-center overflow-hidden rounded-full border border-zinc-200 bg-zinc-100 text-[10px] font-semibold text-zinc-600">
                {channelAvatarUrl ? (
                  <img src={channelAvatarUrl} alt="Avatar" className="h-full w-full object-cover" />
                ) : (
                  getAvatarInitial(channelProfile.channel_name)
                )}
              </div>
              <span className="text-xs font-medium text-zinc-700 max-w-[100px] truncate">
                {channelProfile.channel_name}
              </span>
            </>
          ) : (
            <span className="text-xs font-medium text-amber-600">⚠️ 채널 설정</span>
          )}
        </button>
      </div>
    </div>
  );
}
