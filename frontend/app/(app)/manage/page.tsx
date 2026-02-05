"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import axios from "axios";
import { API_BASE } from "../../constants";
import { useTags } from "../../hooks";
import { useStudioStore } from "../../store/useStudioStore";
import CharacterEditModal from "./CharacterEditModal";
import ManageSidebar, { type ManageTab } from "./ManageSidebar";
import AssetsTab from "./tabs/AssetsTab";
import SettingsTab from "./tabs/SettingsTab";
import TagsTab from "./tabs/TagsTab";
import StyleTab from "./tabs/StyleTab";
import PromptsTab from "./tabs/PromptsTab";
import RenderPresetsTab from "./tabs/RenderPresetsTab";
import VoicePresetsTab from "./tabs/VoicePresetsTab";
import TrashTab from "./tabs/TrashTab";
import YouTubeTab from "./tabs/YouTubeTab";
import type { Character, LoRA } from "../../types";

const VALID_TABS: ManageTab[] = [
  "tags",
  "style",
  "prompts",
  "assets",
  "presets",
  "voice",
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
  const { tags: allTags } = useTags(null);
  const projectId = useStudioStore((s) => s.projectId);

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

  // Enlarged Image State (Global)
  const [enlargedImage, setEnlargedImage] = useState<{ url: string; title: string } | null>(null);

  // Character Editing State
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
  const [isCreatingCharacter, setIsCreatingCharacter] = useState(false);
  const [loraEntries, setLoraEntries] = useState<LoRA[]>([]);

  const fetchLoras = async () => {
    try {
      const res = await axios.get<{ loras: LoRA[] }>(`${API_BASE}/loras/`);
      setLoraEntries(res.data.loras || []);
    } catch {
      console.error("Failed to fetch LoRAs for character modal");
    }
  };

  useEffect(() => {
    void fetchLoras();
  }, []);

  const handleSaveCharacter = async (charData: Partial<Character>) => {
    try {
      if (editingCharacter) {
        await axios.put(`${API_BASE}/characters/${editingCharacter.id}`, charData);
        alert("Character updated!");
      } else {
        await axios.post(`${API_BASE}/characters/`, charData);
        alert("Character created!");
      }
      setEditingCharacter(null);
      setIsCreatingCharacter(false);
    } catch (err) {
      console.error("Failed to save character", err);
      alert("Failed to save character");
    }
  };

  return (
    <div className="flex h-full">
      {/* Sidebar — desktop only */}
      <ManageSidebar activeTab={manageTab} onTabChange={handleTabChange} />

      {/* Mobile tab bar — lg 미만에서만 표시 */}
      <MobileTabBar activeTab={manageTab} onTabChange={handleTabChange} />

      {/* Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="w-full max-w-5xl px-6 py-6">
          {manageTab === "tags" && <TagsTab />}
          {manageTab === "style" && <StyleTab />}
          {manageTab === "prompts" && <PromptsTab />}
          {manageTab === "assets" && <AssetsTab />}
          {manageTab === "presets" && <RenderPresetsTab />}
          {manageTab === "voice" && <VoicePresetsTab />}
          {manageTab === "trash" && <TrashTab />}
          {manageTab === "youtube" && <YouTubeTab projectId={projectId} />}
          {manageTab === "settings" && <SettingsTab />}
        </div>
      </main>

      {/* Global Modals */}
      {enlargedImage && (
        <div
          className="fixed inset-0 z-50 flex cursor-pointer items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setEnlargedImage(null)}
        >
          <div
            className="relative max-h-[90vh] max-w-[90vw] cursor-default"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setEnlargedImage(null)}
              className="absolute -top-3 -right-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white text-zinc-600 shadow-lg hover:bg-zinc-100"
            >
              &#x2715;
            </button>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={enlargedImage.url}
              alt={enlargedImage.title}
              className="max-h-[85vh] max-w-[90vw] rounded-2xl object-contain shadow-2xl"
            />
            <p className="mt-3 text-center text-sm font-medium text-white">{enlargedImage.title}</p>
          </div>
        </div>
      )}

      {(editingCharacter || isCreatingCharacter) && (
        <CharacterEditModal
          character={editingCharacter || undefined}
          allTags={allTags}
          allLoras={loraEntries}
          onClose={() => {
            setEditingCharacter(null);
            setIsCreatingCharacter(false);
          }}
          onSave={handleSaveCharacter}
        />
      )}
    </div>
  );
}

export default function ManagePage() {
  return (
    <Suspense>
      <ManageContent />
    </Suspense>
  );
}

// ── Mobile tab bar (< lg) ────────────────────────────────────

const MOBILE_TABS: { id: ManageTab; label: string }[] = [
  { id: "tags", label: "Tags" },
  { id: "style", label: "Style" },
  { id: "prompts", label: "Prompts" },
  { id: "assets", label: "Assets" },
  { id: "presets", label: "Presets" },
  { id: "voice", label: "Voice" },
  { id: "youtube", label: "YouTube" },
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
    <div className="fixed top-[var(--nav-height)] right-0 left-0 z-20 flex gap-1 overflow-x-auto border-b border-zinc-200 bg-white/90 px-4 py-1.5 backdrop-blur-md lg:hidden">
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
