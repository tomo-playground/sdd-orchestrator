"use client";

import { Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useContextStore } from "../../store/useContextStore";
import {
  Tag,
  Palette,
  FileText,
  SlidersHorizontal,
  Settings,
  Trash2,
  Upload,
} from "lucide-react";

import AppSidebar, { type NavGroup, type NavItem } from "../../components/layout/AppSidebar";
import AppMobileTabBar from "../../components/layout/AppMobileTabBar";
import AppThreeColumnLayout from "../../components/layout/AppThreeColumnLayout";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import ManageSecondaryPanel from "./ManageSecondaryPanel";
import SettingsTab from "./tabs/SettingsTab";
import TagsTab from "./tabs/TagsTab";
import StyleTab from "./tabs/StyleTab";
import PromptsTab from "./tabs/PromptsTab";
import RenderPresetsTab from "./tabs/RenderPresetsTab";
import TrashTab from "./tabs/TrashTab";
import YouTubeTab from "./tabs/YouTubeTab";
import { type ManageTab } from "./types";

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

const NAV_GROUPS: NavGroup[] = [
  {
    key: "library",
    label: "Library",
    items: [
      { id: "tags", label: "Tags", icon: Tag },
      { id: "style", label: "Styles", icon: Palette },
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

const UTILITY_ITEMS: NavItem[] = [
  { id: "prompts", label: "Prompts", icon: FileText },
  { id: "settings", label: "Settings", icon: Settings },
  { id: "trash", label: "Trash", icon: Trash2 },
];

const MOBILE_TABS = [
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

function ManageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = useContextStore((s) => s.projectId);
  const projects = useContextStore((s) => s.projects);
  const projectName = projects.find((p) => p.id === projectId)?.name ?? null;

  // Derive tab directly from URL (no redundant state)
  const tabParam = searchParams.get("tab");
  const manageTab: ManageTab = isValidTab(tabParam) ? tabParam : "tags";

  const handleTabChange = useCallback(
    (tab: ManageTab) => {
      router.replace(`/manage?tab=${tab}`, { scroll: false });
    },
    [router]
  );

  return (
    <AppThreeColumnLayout
      left={
        <AppSidebar
          groups={NAV_GROUPS}
          ungroupedItems={UTILITY_ITEMS}
          activeTab={manageTab}
          onTabChange={handleTabChange}
          collapsedKey="manageSidebarCollapsed"
          collapsedGroupsKey="manageSidebarCollapsedGroups"
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
          {/* Mobile tab bar — lg 미만에서만 표시 */}
          <AppMobileTabBar
            tabs={MOBILE_TABS}
            activeTab={manageTab}
            onTabChange={handleTabChange}
          />

          {/* Content */}
          <div className="px-6 py-6">
            <div className="min-w-0">
              {manageTab === "tags" && <TagsTab />}
              {manageTab === "style" && <StyleTab />}
              {manageTab === "prompts" && <PromptsTab />}
              {manageTab === "presets" && <RenderPresetsTab />}
              {manageTab === "trash" && <TrashTab />}
              {manageTab === "youtube" && <YouTubeTab projectId={projectId} />}
              {manageTab === "settings" && <SettingsTab />}
            </div>
          </div>
        </>
      }
      right={<ManageSecondaryPanel activeTab={manageTab} />}
    />
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
