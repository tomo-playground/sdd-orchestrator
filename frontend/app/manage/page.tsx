"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import { useTags } from "../hooks";
import CharacterEditModal from "./CharacterEditModal";
import AssetsTab from "./tabs/AssetsTab";
import SettingsTab from "./tabs/SettingsTab";
import TagsTab from "./tabs/TagsTab";
import StyleTab from "./tabs/StyleTab";
import PromptsTab from "./tabs/PromptsTab";
import EvaluationTab from "./tabs/EvaluationTab";
import RenderPresetsTab from "./tabs/RenderPresetsTab";
import VoicePresetsTab from "./tabs/VoicePresetsTab";
import TrashTab from "./tabs/TrashTab";
import InsightsTab from "./tabs/InsightsTab";
import type { Character, LoRA } from "../types";

// Manage Tab keys
type ManageTab =
  | "assets"
  | "style"
  | "tags"
  | "prompts"
  | "evaluation"
  | "insights"
  | "presets"
  | "voice"
  | "settings"
  | "trash";

export default function ManagePage() {
  const { tags: allTags } = useTags(null);

  const [manageTab, setManageTab] = useState<ManageTab>("tags");

  // Enlarged Image State (Global)
  const [enlargedImage, setEnlargedImage] = useState<{ url: string; title: string } | null>(null);

  // Character Editing State (Global/Legacy? - Kept for compatibility if triggered externally)
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
  const [isCreatingCharacter, setIsCreatingCharacter] = useState(false);

  // LoRA entries for Character Edit Modal
  const [loraEntries, setLoraEntries] = useState<LoRA[]>([]);

  // Fetch LoRAs for Character Modal
  const fetchLoras = async () => {
    try {
      const res = await axios.get<{ loras: LoRA[] }>(`${API_BASE}/loras/`);
      setLoraEntries(res.data.loras || []);
    } catch {
      console.error("Failed to fetch LoRAs for character modal");
    }
  };

  useEffect(() => {
    // We only need to fetch these if the modal is likely to be used,
    // or if we want to keep ManagePage state ready.
    // For now, we fetch once on mount to ensure data availability if the modal opens.
    void fetchLoras(); // eslint-disable-line react-hooks/set-state-in-effect
  }, []);

  // Handle saving a character from the modal
  const handleSaveCharacter = async (charData: Partial<Character>) => {
    try {
      if (editingCharacter) {
        // Update
        await axios.put(`${API_BASE}/characters/${editingCharacter.id}`, charData);
        alert("Character updated!");
      } else {
        // Create
        await axios.post(`${API_BASE}/characters/`, charData);
        alert("Character created!");
      }
      setEditingCharacter(null);
      setIsCreatingCharacter(false);
      // We might want to refresh lists if we had a Characters list here.
    } catch (err) {
      console.error("Failed to save character", err);
      alert("Failed to save character");
    }
  };

  return (
    <main className="flex w-full max-w-5xl flex-col gap-8 px-6 py-6">
      {/* Navigation Tabs */}
      <div className="flex gap-1 overflow-x-auto rounded-xl bg-zinc-100/60 p-1">
        {[
          { id: "tags", label: "Tags" },
          { id: "style", label: "Style" },
          { id: "prompts", label: "Prompts" },
          { id: "evaluation", label: "Eval" },
          { id: "insights", label: "Insights" },
          { id: "assets", label: "Assets" },
          { id: "presets", label: "Presets" },
          { id: "voice", label: "Voice" },
          { id: "settings", label: "Settings" },
          { id: "trash", label: "Trash" },
        ].map((tab) => {
          const active = manageTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setManageTab(tab.id as ManageTab)}
              className={`shrink-0 rounded-lg px-3 py-2 text-xs font-semibold transition ${
                active ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-700"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content -- Now Modularized */}

      {manageTab === "tags" && <TagsTab />}

      {manageTab === "style" && <StyleTab />}

      {manageTab === "prompts" && <PromptsTab />}

      {manageTab === "evaluation" && <EvaluationTab />}

      {manageTab === "insights" && <InsightsTab />}

      {manageTab === "assets" && <AssetsTab />}

      {manageTab === "presets" && <RenderPresetsTab />}

      {manageTab === "voice" && <VoicePresetsTab />}

      {manageTab === "settings" && <SettingsTab />}

      {manageTab === "trash" && <TrashTab />}

      {/* Global Modals */}

      {/* Enlarged Image Modal */}
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
              ✕
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

      {/* Character Edit Modal */}
      {/* Note: This modal's trigger is currently not exposed in the new UI structure 
            but kept for backward compatibility or if triggered programmatically. */}
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
    </main>
  );
}
