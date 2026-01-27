"use client";

import { useState, useMemo, useEffect } from "react";
import { Character, CharacterLoRA, Tag, LoRA, ActorGender, PromptMode } from "../types";
import LoadingSpinner from "../components/ui/LoadingSpinner";

type Props = {
  character: Character;
  allTags: Tag[];
  allLoras: LoRA[];
  onClose: () => void;
  onSave: (id: number, data: Partial<Character>) => Promise<void>;
};

export default function CharacterEditModal({
  character,
  allTags,
  allLoras,
  onClose,
  onSave,
}: Props) {
  const [name, setName] = useState(character.name);
  const [description, setDescription] = useState(character.description || "");
  const [gender, setGender] = useState<ActorGender>(character.gender || "female");
  const [previewImageUrl, setPreviewImageUrl] = useState(character.preview_image_url || "");
  const [promptMode, setPromptMode] = useState<PromptMode>("auto"); // Default to auto if not present in type (it is in type now)

  // Tags state
  const [identityTagIds, setIdentityTagIds] = useState<number[]>(character.identity_tags || []);
  const [clothingTagIds, setClothingTagIds] = useState<number[]>(character.clothing_tags || []);
  const [tagSearch, setTagSearch] = useState("");
  const [activeTagInput, setActiveTagInput] = useState<"identity" | "clothing" | null>(null);

  // LoRAs state
  const [selectedLoras, setSelectedLoras] = useState<CharacterLoRA[]>(character.loras || []);
  const [isSaving, setIsSaving] = useState(false);

  // Initialize prompt_mode if it exists in character object (it might be missing in older types, but we saw it in schema)
  useEffect(() => {
    if ((character as any).prompt_mode) {
      setPromptMode((character as any).prompt_mode);
    }
  }, [character]);

  // Derived state for tags
  const identityTags = useMemo(() => 
    identityTagIds.map(id => allTags.find(t => t.id === id)).filter(Boolean) as Tag[],
    [identityTagIds, allTags]
  );
  
  const clothingTags = useMemo(() => 
    clothingTagIds.map(id => allTags.find(t => t.id === id)).filter(Boolean) as Tag[],
    [clothingTagIds, allTags]
  );

  const filteredTags = useMemo(() => {
    if (!tagSearch.trim()) return [];
    const search = tagSearch.toLowerCase();
    return allTags
      .filter(t => t.name.toLowerCase().includes(search))
      .slice(0, 10); // Limit to 10 suggestions
  }, [allTags, tagSearch]);

  const handleAddTag = (tag: Tag) => {
    if (activeTagInput === "identity") {
      if (!identityTagIds.includes(tag.id)) {
        setIdentityTagIds([...identityTagIds, tag.id]);
      }
    } else if (activeTagInput === "clothing") {
      if (!clothingTagIds.includes(tag.id)) {
        setClothingTagIds([...clothingTagIds, tag.id]);
      }
    }
    setTagSearch("");
    // Keep focus? Maybe not needed for now
  };

  const handleRemoveTag = (id: number, type: "identity" | "clothing") => {
    if (type === "identity") {
      setIdentityTagIds(identityTagIds.filter(t => t !== id));
    } else {
      setClothingTagIds(clothingTagIds.filter(t => t !== id));
    }
  };

  const handleAddLora = () => {
    // Add a placeholder or the first available LoRA
    if (allLoras.length > 0) {
      const first = allLoras[0];
      // Check if already added? Maybe allow duplicates with different weights? Usually not.
      if (!selectedLoras.find(l => l.lora_id === first.id)) {
        setSelectedLoras([...selectedLoras, { lora_id: first.id, weight: 1.0 }]);
      }
    }
  };

  const handleUpdateLora = (index: number, field: "lora_id" | "weight", value: number) => {
    const newLoras = [...selectedLoras];
    newLoras[index] = { ...newLoras[index], [field]: value };
    setSelectedLoras(newLoras);
  };

  const handleRemoveLora = (index: number) => {
    setSelectedLoras(selectedLoras.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    setIsSaving(true);
    try {
      await onSave(character.id, {
        name,
        description,
        gender,
        preview_image_url: previewImageUrl,
        identity_tags: identityTagIds,
        clothing_tags: clothingTagIds,
        loras: selectedLoras,
        prompt_mode: promptMode,
      });
      onClose();
    } catch (error) {
      console.error("Failed to save character", error);
      alert("Failed to save changes");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="w-full max-w-2xl bg-white rounded-3xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-100 flex justify-between items-center bg-zinc-50/50">
          <h2 className="text-lg font-bold text-zinc-900">Edit Character: {character.name}</h2>
          <button onClick={onClose} className="text-zinc-400 hover:text-zinc-600">✕</button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* Basic Info */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Gender</label>
              <select
                value={gender || "female"}
                onChange={(e) => setGender(e.target.value as ActorGender)}
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400 bg-white"
              >
                <option value="female">Female</option>
                <option value="male">Male</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400 resize-none"
            />
          </div>
          
           <div>
            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Preview Image URL</label>
            <input
              value={previewImageUrl}
              onChange={(e) => setPreviewImageUrl(e.target.value)}
              className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-xs font-mono text-zinc-600 outline-none focus:border-zinc-400"
            />
          </div>
          
          <div>
             <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Prompt Mode</label>
             <select
                value={promptMode}
                onChange={(e) => setPromptMode(e.target.value as PromptMode)}
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400 bg-white"
             >
                <option value="auto">Auto (Smart Compose)</option>
                <option value="standard">Standard (No LoRA)</option>
                <option value="lora">LoRA Only</option>
             </select>
             <p className="text-[10px] text-zinc-400 mt-1">
               Auto: Automatically decides whether to use LoRA based on prompt complexity.<br/>
               Standard: Forces standard generation.<br/>
               LoRA: Forces usage of character LoRAs.
             </p>
          </div>

          {/* Identity Tags */}
          <div>
            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Identity Tags</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {identityTags.map(tag => (
                <span key={tag.id} className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-2 py-1 text-xs text-purple-700">
                  {tag.name}
                  <button onClick={() => handleRemoveTag(tag.id, "identity")} className="hover:text-purple-900">×</button>
                </span>
              ))}
              <div className="relative">
                <input
                  value={activeTagInput === "identity" ? tagSearch : ""}
                  onChange={(e) => {
                    setActiveTagInput("identity");
                    setTagSearch(e.target.value);
                  }}
                  onFocus={() => setActiveTagInput("identity")}
                  placeholder="+ Add tag"
                  className="rounded-full border border-dashed border-zinc-300 px-3 py-1 text-xs outline-none focus:border-zinc-400 w-24 focus:w-48 transition-all"
                />
                {activeTagInput === "identity" && tagSearch && filteredTags.length > 0 && (
                  <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-zinc-200 rounded-xl shadow-lg z-10 max-h-40 overflow-y-auto">
                    {filteredTags.map(tag => (
                      <button
                        key={tag.id}
                        onClick={() => handleAddTag(tag)}
                        className="w-full text-left px-3 py-2 text-xs hover:bg-zinc-50"
                      >
                        {tag.name} <span className="text-zinc-400 text-[10px]">({tag.category})</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Clothing Tags */}
          <div>
            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Clothing Tags</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {clothingTags.map(tag => (
                <span key={tag.id} className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-xs text-amber-700">
                  {tag.name}
                  <button onClick={() => handleRemoveTag(tag.id, "clothing")} className="hover:text-amber-900">×</button>
                </span>
              ))}
               <div className="relative">
                <input
                  value={activeTagInput === "clothing" ? tagSearch : ""}
                  onChange={(e) => {
                    setActiveTagInput("clothing");
                    setTagSearch(e.target.value);
                  }}
                   onFocus={() => setActiveTagInput("clothing")}
                  placeholder="+ Add tag"
                  className="rounded-full border border-dashed border-zinc-300 px-3 py-1 text-xs outline-none focus:border-zinc-400 w-24 focus:w-48 transition-all"
                />
                 {activeTagInput === "clothing" && tagSearch && filteredTags.length > 0 && (
                  <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-zinc-200 rounded-xl shadow-lg z-10 max-h-40 overflow-y-auto">
                    {filteredTags.map(tag => (
                      <button
                        key={tag.id}
                        onClick={() => handleAddTag(tag)}
                        className="w-full text-left px-3 py-2 text-xs hover:bg-zinc-50"
                      >
                        {tag.name} <span className="text-zinc-400 text-[10px]">({tag.category})</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* LoRAs */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider">LoRAs</label>
              <button
                onClick={handleAddLora}
                className="text-[10px] font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50 px-2 py-1 rounded-full"
              >
                + Add LoRA
              </button>
            </div>
            
            <div className="space-y-2">
              {selectedLoras.map((lora, index) => (
                <div key={index} className="flex items-center gap-2 p-2 rounded-xl border border-zinc-100 bg-zinc-50/50">
                  <select
                    value={lora.lora_id}
                    onChange={(e) => handleUpdateLora(index, "lora_id", Number(e.target.value))}
                    className="flex-1 rounded-lg border border-zinc-200 px-2 py-1.5 text-xs outline-none focus:border-zinc-400 bg-white"
                  >
                    {allLoras.map(l => (
                      <option key={l.id} value={l.id}>{l.display_name || l.name}</option>
                    ))}
                  </select>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={lora.weight}
                    onChange={(e) => handleUpdateLora(index, "weight", Number(e.target.value))}
                    className="w-16 rounded-lg border border-zinc-200 px-2 py-1.5 text-xs outline-none focus:border-zinc-400 text-center"
                  />
                  <button onClick={() => handleRemoveLora(index)} className="text-rose-400 hover:text-rose-600 px-1">
                    ✕
                  </button>
                </div>
              ))}
              {selectedLoras.length === 0 && (
                <p className="text-xs text-zinc-400 italic">No LoRAs assigned.</p>
              )}
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-zinc-100 flex justify-end gap-3 bg-zinc-50/50">
          <button
            onClick={onClose}
            className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-50"
            disabled={isSaving}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSaving}
            className="rounded-full bg-zinc-900 px-6 py-2 text-xs font-semibold text-white hover:bg-zinc-800 disabled:opacity-50 flex items-center gap-2"
          >
            {isSaving && <LoadingSpinner size="sm" color="text-white/50" />}
            {isSaving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
