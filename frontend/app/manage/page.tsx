"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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
import type { Character, Tag, LoRA } from "../types";

// Manage Tab keys
type ManageTab = "assets" | "style" | "tags" | "prompts" | "evaluation" | "presets" | "settings";

export default function ManagePage() {
  const { tags: allTags, reload: fetchTagsData } = useTags(null);

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
    void fetchLoras();
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
    <div className="min-h-screen bg-gradient-to-br from-zinc-50 via-white to-zinc-100 text-zinc-900">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-zinc-200/60 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <h1 className="text-lg font-bold tracking-tight text-zinc-900">
            Manage
          </h1>
          <Link
            href="/"
            className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-50 transition"
          >
            Home
          </Link>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-6">
        {/* Navigation Tabs */}
        <div className="flex flex-wrap items-center gap-2">
          {[
            { id: "tags", label: "Tags" },
            { id: "style", label: "Style" },
            { id: "prompts", label: "Prompts" },
            { id: "evaluation", label: "Eval" },
            { id: "assets", label: "Assets" },
            { id: "presets", label: "Presets" },
            { id: "settings", label: "Settings" },
          ].map((tab) => {
            const active = manageTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setManageTab(tab.id as ManageTab)}
                className={`rounded-full px-4 py-2 text-[10px] font-semibold tracking-[0.2em] uppercase transition ${active
                  ? "bg-zinc-900 text-white"
                  : "border border-zinc-200 bg-white text-zinc-600"
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

        {manageTab === "assets" && <AssetsTab />}

        {manageTab === "presets" && <RenderPresetsTab />}

        {manageTab === "settings" && <SettingsTab />}

        {/* Global Modals */}

        {/* Enlarged Image Modal */}
        {enlargedImage && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm cursor-pointer"
            onClick={() => setEnlargedImage(null)}
          >
            <div
              className="relative max-w-[90vw] max-h-[90vh] cursor-default"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                onClick={() => setEnlargedImage(null)}
                className="absolute -top-3 -right-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white text-zinc-600 shadow-lg hover:bg-zinc-100"
              >
                ✕
              </button>
              <img
                src={enlargedImage.url}
                alt={enlargedImage.title}
                className="max-w-[90vw] max-h-[85vh] rounded-2xl object-contain shadow-2xl"
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
    </div>
  );
}
