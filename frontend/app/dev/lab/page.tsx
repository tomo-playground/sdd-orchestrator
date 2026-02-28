"use client";

import { Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import LabSidebar, { type LabTab } from "../../admin/lab/LabSidebar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import TagLabTab from "../../admin/lab/tabs/TagLabTab";
import SceneLabTab from "../../admin/lab/tabs/SceneLabTab";
import AnalyticsTab from "../../admin/lab/tabs/AnalyticsTab";
import TagBrowserTab from "../../admin/lab/tabs/TagBrowserTab";

const VALID_TABS: LabTab[] = ["tag-lab", "scene-lab", "analytics", "tag-browser"];

function isValidTab(v: string | null): v is LabTab {
  return v !== null && VALID_TABS.includes(v as LabTab);
}

function LabContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const tabParam = searchParams.get("tab");
  const activeTab: LabTab = isValidTab(tabParam) ? tabParam : "tag-lab";

  const handleTabChange = useCallback(
    (tab: LabTab) => {
      router.replace(`/dev/lab?tab=${tab}`, { scroll: false });
    },
    [router],
  );

  return (
    <div className="flex h-full">
      <LabSidebar activeTab={activeTab} onTabChange={handleTabChange} />

      <main className="flex-1 overflow-y-auto">
        <div className="w-full px-8 py-6">
          {activeTab === "tag-lab" && <TagLabTab />}
          {activeTab === "scene-lab" && <SceneLabTab />}
          {activeTab === "analytics" && <AnalyticsTab />}
          {activeTab === "tag-browser" && <TagBrowserTab />}
        </div>
      </main>
    </div>
  );
}

export default function DevLabPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      }
    >
      <LabContent />
    </Suspense>
  );
}
