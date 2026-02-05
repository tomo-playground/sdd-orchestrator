"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import QualitySidebar, { type QualityTab } from "./QualitySidebar";
import EvaluationTab from "./tabs/EvaluationTab";
import InsightsTab from "./tabs/InsightsTab";

const VALID_TABS: QualityTab[] = ["evaluation", "insights"];

function isValidTab(v: string | null): v is QualityTab {
  return v !== null && VALID_TABS.includes(v as QualityTab);
}

function QualityContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const tabParam = searchParams.get("tab");
  const [activeTab, setActiveTab] = useState<QualityTab>(
    isValidTab(tabParam) ? tabParam : "evaluation"
  );

  useEffect(() => {
    if (isValidTab(tabParam) && tabParam !== activeTab) {
      setActiveTab(tabParam);
    }
  }, [tabParam]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleTabChange = useCallback(
    (tab: QualityTab) => {
      setActiveTab(tab);
      router.replace(`/quality?tab=${tab}`, { scroll: false });
    },
    [router]
  );

  return (
    <div className="flex h-full">
      <QualitySidebar activeTab={activeTab} onTabChange={handleTabChange} />
      <MobileTabBar activeTab={activeTab} onTabChange={handleTabChange} />

      <main className="flex-1 overflow-y-auto">
        <div className="w-full max-w-5xl px-6 py-6">
          {activeTab === "evaluation" && <EvaluationTab />}
          {activeTab === "insights" && <InsightsTab />}
        </div>
      </main>
    </div>
  );
}

export default function QualityPage() {
  return (
    <Suspense>
      <QualityContent />
    </Suspense>
  );
}

// ── Mobile tab bar (< lg) ────────────────────────────────────

const MOBILE_TABS: { id: QualityTab; label: string }[] = [
  { id: "evaluation", label: "Eval" },
  { id: "insights", label: "Insights" },
];

function MobileTabBar({
  activeTab,
  onTabChange,
}: {
  activeTab: QualityTab;
  onTabChange: (tab: QualityTab) => void;
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
              active ? "bg-zinc-900 text-white" : "text-zinc-500 hover:text-zinc-700"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
