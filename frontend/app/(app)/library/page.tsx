"use client";

import { Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Users, Mic, Music, Image, Tag, Palette, FileText } from "lucide-react";

import AppSidebar, { type NavGroup } from "../../components/layout/AppSidebar";
import AppMobileTabBar from "../../components/layout/AppMobileTabBar";
import AppThreeColumnLayout from "../../components/layout/AppThreeColumnLayout";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import LibrarySecondaryPanel from "./LibrarySecondaryPanel";
import { CharactersContent } from "../characters/page";
import { VoicesContent } from "../voices/page";
import { MusicContent } from "../music/page";
import { BackgroundsContent } from "../backgrounds/page";
import TagsTab from "./tabs/TagsTab";
import StyleTab from "./tabs/StyleTab";
import PromptsTab from "./tabs/PromptsTab";
import { type LibraryTab } from "./types";

const VALID_TABS: LibraryTab[] = [
  "characters",
  "voices",
  "music",
  "backgrounds",
  "tags",
  "style",
  "prompts",
];

function isValidTab(v: string | null): v is LibraryTab {
  return v !== null && VALID_TABS.includes(v as LibraryTab);
}

const NAV_GROUPS: NavGroup[] = [
  {
    key: "visuals",
    label: "Visuals",
    items: [
      { id: "characters", label: "Characters", icon: Users },
      { id: "backgrounds", label: "Backgrounds", icon: Image },
      { id: "style", label: "Styles", icon: Palette },
    ],
  },
  {
    key: "audio",
    label: "Audio",
    items: [
      { id: "voices", label: "Voices", icon: Mic },
      { id: "music", label: "Music", icon: Music },
    ],
  },
  {
    key: "text",
    label: "Text & Meta",
    items: [
      { id: "prompts", label: "Prompts", icon: FileText },
      { id: "tags", label: "Tags", icon: Tag },
    ],
  },
];

const MOBILE_TABS = [
  { id: "characters", label: "Characters" },
  { id: "voices", label: "Voices" },
  { id: "music", label: "Music" },
  { id: "backgrounds", label: "Backgrounds" },
  { id: "style", label: "Styles" },
  { id: "prompts", label: "Prompts" },
  { id: "tags", label: "Tags" },
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
          groups={NAV_GROUPS}
          activeTab={activeTab}
          onTabChange={handleTabChange}
          collapsedKey="librarySidebarCollapsed"
          collapsedGroupsKey="librarySidebarCollapsedGroups"
        />
      }
      center={
        <>
          {/* Mobile tab bar */}
          <AppMobileTabBar tabs={MOBILE_TABS} activeTab={activeTab} onTabChange={handleTabChange} />
          <div className="min-w-0 px-8 py-6">
            {activeTab === "characters" && <CharactersContent />}
            {activeTab === "voices" && <VoicesContent />}
            {activeTab === "music" && <MusicContent />}
            {activeTab === "backgrounds" && <BackgroundsContent />}
            {activeTab === "tags" && <TagsTab />}
            {activeTab === "style" && <StyleTab />}
            {activeTab === "prompts" && <PromptsTab />}
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
