"use client";

import { Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import LibrarySidebar, { type LibraryTab } from "./LibrarySidebar";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import {
  TAB_ACTIVE,
  TAB_INACTIVE,
  PAGE_2COL_LAYOUT,
  SECONDARY_PANEL_CLASSES,
} from "../../components/ui/variants";
import LibrarySecondaryPanel from "./LibrarySecondaryPanel";
import { CharactersContent } from "../characters/page";
import { VoicesContent } from "../voices/page";
import { MusicContent } from "../music/page";
import { BackgroundsContent } from "../backgrounds/page";

const VALID_TABS: LibraryTab[] = ["characters", "voices", "music", "backgrounds"];

function isValidTab(v: string | null): v is LibraryTab {
  return v !== null && VALID_TABS.includes(v as LibraryTab);
}

function LibraryContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const tabParam = searchParams.get("tab");
  const activeTab: LibraryTab = isValidTab(tabParam) ? tabParam : "characters";

  const handleTabChange = useCallback(
    (tab: LibraryTab) => {
      router.replace(`/library?tab=${tab}`, { scroll: false });
    },
    [router]
  );

  return (
    <div className="flex h-full">
      <LibrarySidebar activeTab={activeTab} onTabChange={handleTabChange} />

      {/* Mobile tab bar */}
      <MobileTabBar activeTab={activeTab} onTabChange={handleTabChange} />

      <main className="flex-1 overflow-y-auto px-6">
        <div className={PAGE_2COL_LAYOUT}>
          <div className="min-w-0">
            {activeTab === "characters" && <CharactersContent />}
            {activeTab === "voices" && <VoicesContent />}
            {activeTab === "music" && <MusicContent />}
            {activeTab === "backgrounds" && <BackgroundsContent />}
          </div>
          <div className={SECONDARY_PANEL_CLASSES}>
            <LibrarySecondaryPanel activeTab={activeTab} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default function LibraryPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      }
    >
      <LibraryContent />
    </Suspense>
  );
}

// -- Mobile tab bar (< lg) --

const MOBILE_TABS: { id: LibraryTab; label: string }[] = [
  { id: "characters", label: "Characters" },
  { id: "voices", label: "Voices" },
  { id: "music", label: "Music" },
  { id: "backgrounds", label: "Backgrounds" },
];

function MobileTabBar({
  activeTab,
  onTabChange,
}: {
  activeTab: LibraryTab;
  onTabChange: (tab: LibraryTab) => void;
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
