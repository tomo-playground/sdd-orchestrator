"use client";

import { Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Brain, SlidersHorizontal, Settings, Trash2, Upload } from "lucide-react";

import AppSidebar, { type NavGroup, type NavItem } from "../../components/layout/AppSidebar";
import AppMobileTabBar from "../../components/layout/AppMobileTabBar";
import AppThreeColumnLayout from "../../components/layout/AppThreeColumnLayout";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import SettingsSecondaryPanel from "./SettingsSecondaryPanel";
import GeneralSettingsTab from "./tabs/GeneralSettingsTab";
import RenderPresetsTab from "./tabs/RenderPresetsTab";
import MemoryTab from "./tabs/MemoryTab";
import TrashTab from "./tabs/TrashTab";
import YouTubeConnectTab from "./tabs/YouTubeConnectTab";
import { type SettingsTab } from "./types";
import { useContextStore } from "../../store/useContextStore";

const VALID_TABS: SettingsTab[] = ["general", "presets", "youtube", "trash", "memory"];

function isValidTab(v: string | null): v is SettingsTab {
  return v !== null && VALID_TABS.includes(v as SettingsTab);
}

const NAV_GROUPS: NavGroup[] = [
  {
    key: "general",
    label: "General",
    items: [
      { id: "general", label: "App Settings", icon: Settings },
      { id: "memory", label: "AI Memory", icon: Brain },
    ],
  },
  {
    key: "project",
    label: "Project",
    items: [
      { id: "presets", label: "Render Presets", icon: SlidersHorizontal },
      { id: "youtube", label: "YouTube", icon: Upload },
    ],
  },
];

const SYSTEM_ITEMS: NavItem[] = [{ id: "trash", label: "Trash", icon: Trash2 }];

const MOBILE_TABS = [
  { id: "general", label: "General" },
  { id: "presets", label: "Presets" },
  { id: "youtube", label: "YouTube" },
  { id: "trash", label: "Trash" },
  { id: "memory", label: "Memory" },
];

function SettingsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = useContextStore((s) => s.projectId);
  const projects = useContextStore((s) => s.projects);
  const projectName = projects.find((p) => p.id === projectId)?.name ?? null;

  // Derive tab directly from URL
  const tabParam = searchParams.get("tab");
  const activeTab: SettingsTab = isValidTab(tabParam) ? tabParam : "general";

  const handleTabChange = useCallback(
    (tab: SettingsTab) => {
      router.replace(`/settings?tab=${tab}`, { scroll: false });
    },
    [router]
  );

  return (
    <AppThreeColumnLayout
      left={
        <AppSidebar
          groups={NAV_GROUPS}
          ungroupedItems={SYSTEM_ITEMS}
          activeTab={activeTab}
          onTabChange={handleTabChange}
          collapsedKey="settingsSidebarCollapsed"
          collapsedGroupsKey="settingsSidebarCollapsedGroups"
          headerContent={
            projectName && (
              <span className="ml-auto max-w-[7rem] truncate text-[11px] font-medium text-zinc-400">
                {projectName}
              </span>
            )
          }
        />
      }
      center={
        <>
          {/* Mobile tab bar */}
          <AppMobileTabBar tabs={MOBILE_TABS} activeTab={activeTab} onTabChange={handleTabChange} />

          {/* Content */}
          <div className="min-w-0 px-8 py-6">
            {activeTab === "general" && <GeneralSettingsTab />}
            {activeTab === "presets" && <RenderPresetsTab />}
            {activeTab === "youtube" && <YouTubeConnectTab projectId={projectId} />}
            {activeTab === "trash" && <TrashTab />}
            {activeTab === "memory" && <MemoryTab />}
          </div>
        </>
      }
      right={<SettingsSecondaryPanel activeTab={activeTab} />}
    />
  );
}

export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      }
    >
      <SettingsContent />
    </Suspense>
  );
}
