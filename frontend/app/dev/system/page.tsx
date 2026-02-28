"use client";

import { Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { cx, TAB_ACTIVE, TAB_INACTIVE } from "../../components/ui/variants";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import GeneralSettingsTab from "../../admin/system/tabs/GeneralSettingsTab";
import MemoryTab from "../../admin/system/tabs/MemoryTab";

type DevSystemTab = "general" | "memory";

const VALID_TABS: DevSystemTab[] = ["general", "memory"];
const TABS = [
  { id: "general" as const, label: "General" },
  { id: "memory" as const, label: "Memory" },
];

function isValidTab(v: string | null): v is DevSystemTab {
  return v !== null && VALID_TABS.includes(v as DevSystemTab);
}

function SystemContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const tabParam = searchParams.get("tab");
  const activeTab: DevSystemTab = isValidTab(tabParam) ? tabParam : "general";

  const handleTabChange = useCallback(
    (tab: DevSystemTab) => {
      router.replace(`/dev/system?tab=${tab}`, { scroll: false });
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

      {activeTab === "general" && <GeneralSettingsTab />}
      {activeTab === "memory" && <MemoryTab />}
    </div>
  );
}

export default function DevSystemPage() {
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
