"use client";

import { Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { cx, TAB_ACTIVE, TAB_INACTIVE } from "../../components/ui/variants";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
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

const TABS = [
  { id: "general" as const, label: "General" },
  { id: "presets" as const, label: "Presets" },
  { id: "youtube" as const, label: "YouTube" },
  { id: "memory" as const, label: "Memory" },
  { id: "trash" as const, label: "Trash" },
];

function SystemContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = useContextStore((s) => s.projectId);

  const tabParam = searchParams.get("tab");
  const activeTab: SettingsTab = isValidTab(tabParam) ? tabParam : "general";

  const handleTabChange = useCallback(
    (tab: SettingsTab) => {
      router.replace(`/admin/system?tab=${tab}`, { scroll: false });
    },
    [router],
  );

  return (
    <div className="px-8 py-6">
      {/* Tab bar */}
      <div className="mb-6 flex items-center gap-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={cx(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition",
              activeTab === tab.id ? TAB_ACTIVE : TAB_INACTIVE,
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === "general" && <GeneralSettingsTab />}
      {activeTab === "presets" && <RenderPresetsTab />}
      {activeTab === "youtube" && <YouTubeConnectTab projectId={projectId} />}
      {activeTab === "trash" && <TrashTab />}
      {activeTab === "memory" && <MemoryTab />}
    </div>
  );
}

export default function AdminSystemPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      }
    >
      <SystemContent />
    </Suspense>
  );
}
