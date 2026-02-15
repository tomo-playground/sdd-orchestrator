"use client";

import { Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Users, Mic, Music, Image } from "lucide-react";

import AppSidebar, { type NavItem } from "../../components/layout/AppSidebar";
import AppMobileTabBar from "../../components/layout/AppMobileTabBar";
import AppThreeColumnLayout from "../../components/layout/AppThreeColumnLayout";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import LibrarySecondaryPanel from "./LibrarySecondaryPanel";
import { CharactersContent } from "../characters/page";
import { VoicesContent } from "../voices/page";
import { MusicContent } from "../music/page";
import { BackgroundsContent } from "../backgrounds/page";
import { type LibraryTab } from "./types";

const VALID_TABS: LibraryTab[] = ["characters", "voices", "music", "backgrounds"];

function isValidTab(v: string | null): v is LibraryTab {
  return v !== null && VALID_TABS.includes(v as LibraryTab);
}

const NAV_ITEMS: NavItem[] = [
  { id: "characters", label: "Characters", icon: Users },
  { id: "voices", label: "Voices", icon: Mic },
  { id: "music", label: "Music", icon: Music },
  { id: "backgrounds", label: "Backgrounds", icon: Image },
];

const MOBILE_TABS = [
  { id: "characters", label: "Characters" },
  { id: "voices", label: "Voices" },
  { id: "music", label: "Music" },
  { id: "backgrounds", label: "Backgrounds" },
];

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
    <AppThreeColumnLayout
      left={
        <AppSidebar
          items={NAV_ITEMS}
          activeTab={activeTab}
          onTabChange={handleTabChange}
          collapsedKey="librarySidebarCollapsed"
        />
      }
      center={
        <>
          {/* Mobile tab bar */}
          <AppMobileTabBar
            tabs={MOBILE_TABS}
            activeTab={activeTab}
            onTabChange={handleTabChange}
          />
          <div className="px-6 py-6 min-w-0">
            {activeTab === "characters" && <CharactersContent />}
            {activeTab === "voices" && <VoicesContent />}
            {activeTab === "music" && <MusicContent />}
            {activeTab === "backgrounds" && <BackgroundsContent />}
          </div>
        </>
      }
      right={<LibrarySecondaryPanel activeTab={activeTab} />}
    />
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
