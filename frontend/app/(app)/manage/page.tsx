"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useContextStore } from "../../store/useContextStore";
import ManageSidebar, { type ManageTab } from "./ManageSidebar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import { TAB_ACTIVE, TAB_INACTIVE } from "../../components/ui/variants";
import SettingsTab from "./tabs/SettingsTab";
import TagsTab from "./tabs/TagsTab";
import StyleTab from "./tabs/StyleTab";
import PromptsTab from "./tabs/PromptsTab";
import RenderPresetsTab from "./tabs/RenderPresetsTab";
import TrashTab from "./tabs/TrashTab";
import YouTubeTab from "./tabs/YouTubeTab";

const VALID_TABS: ManageTab[] = [
  "tags",
  "style",
  "prompts",
  "presets",
  "youtube",
  "settings",
  "trash",
];

function isValidTab(v: string | null): v is ManageTab {
  return v !== null && VALID_TABS.includes(v as ManageTab);
}

function ManageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = useContextStore((s) => s.projectId);

  // URL-synced tab state
  const tabParam = searchParams.get("tab");
  const [manageTab, setManageTab] = useState<ManageTab>(isValidTab(tabParam) ? tabParam : "tags");

  // Sync state when URL changes externally
  useEffect(() => {
    if (isValidTab(tabParam) && tabParam !== manageTab) {
      setManageTab(tabParam);
    }
  }, [tabParam]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleTabChange = useCallback(
    (tab: ManageTab) => {
      setManageTab(tab);
      router.replace(`/manage?tab=${tab}`, { scroll: false });
    },
    [router]
  );

  return (
    <div className="flex h-full">
      {/* Sidebar — desktop only */}
      <ManageSidebar activeTab={manageTab} onTabChange={handleTabChange} />

      {/* Mobile tab bar — lg 미만에서만 표시 */}
      <MobileTabBar activeTab={manageTab} onTabChange={handleTabChange} />

      {/* Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-7xl px-6 py-6">
          {manageTab === "tags" && <TagsTab />}
          {manageTab === "style" && <StyleTab />}
          {manageTab === "prompts" && <PromptsTab />}
          {manageTab === "presets" && <RenderPresetsTab />}
          {manageTab === "trash" && <TrashTab />}
          {manageTab === "youtube" && <YouTubeTab projectId={projectId} />}
          {manageTab === "settings" && <SettingsTab />}
        </div>
      </main>
    </div>
  );
}

export default function ManagePage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      }
    >
      <ManageContent />
    </Suspense>
  );
}

// ── Mobile tab bar (< lg) ────────────────────────────────────

const MOBILE_TABS: { id: ManageTab; label: string }[] = [
  // Library
  { id: "tags", label: "Tags" },
  { id: "style", label: "Styles" },
  // Project
  { id: "presets", label: "Presets" },
  { id: "youtube", label: "YouTube" },
  // Utility
  { id: "prompts", label: "Prompts" },
  { id: "settings", label: "Settings" },
  { id: "trash", label: "Trash" },
];

function MobileTabBar({
  activeTab,
  onTabChange,
}: {
  activeTab: ManageTab;
  onTabChange: (tab: ManageTab) => void;
}) {
  return (
    <div className="fixed top-[var(--nav-height)] right-0 left-0 z-[var(--z-sticky)] flex gap-1 overflow-x-auto border-b border-zinc-200 bg-white/90 px-4 py-1.5 backdrop-blur-md lg:hidden">
      {MOBILE_TABS.map((tab) => {
        const active = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onTabChange(tab.id)}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              active ? TAB_ACTIVE : TAB_INACTIVE
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
