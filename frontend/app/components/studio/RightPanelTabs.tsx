"use client";

import type { ReactNode } from "react";
import { useUIStore, type RightPanelTab } from "../../store/useUIStore";
import { RIGHT_PANEL_CLASSES } from "../ui/variants";

const TABS: { key: RightPanelTab; label: string }[] = [
  { key: "image", label: "Image" },
  { key: "tools", label: "Tools" },
  { key: "insight", label: "Insight" },
];

type RightPanelTabsProps = {
  imageContent: ReactNode;
  toolsContent: ReactNode;
  insightContent: ReactNode;
};

export default function RightPanelTabs({
  imageContent,
  toolsContent,
  insightContent,
}: RightPanelTabsProps) {
  const activeTab = useUIStore((s) => s.rightPanelTab);
  const setTab = useUIStore((s) => s.set);

  return (
    <aside className={RIGHT_PANEL_CLASSES}>
      {/* Tab Bar */}
      <div className="flex gap-1 rounded-lg bg-zinc-100 p-0.5">
        {TABS.map((tab) => {
          const active = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setTab({ rightPanelTab: tab.key })}
              className={`flex-1 rounded-md px-2 py-1 text-xs font-semibold transition ${
                active ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-700"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {activeTab === "image" && imageContent}
      {activeTab === "tools" && toolsContent}
      {activeTab === "insight" && insightContent}
    </aside>
  );
}
