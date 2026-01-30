"use client";

import { useState, useMemo, useEffect } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import { Character, CharacterLoRA, Tag, LoRA, ActorGender, PromptMode } from "../types";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import ImagePreviewModal from "../components/ui/ImagePreviewModal";

type Props = {
  character?: Character; // Make character optional for create mode
  allTags: Tag[];
  allLoras: LoRA[];
  onClose: () => void;
  onSave: (data: Partial<Character>, id?: number) => Promise<void>; // Update onSave signature
};

export default function CharacterEditModal({
  character,
  allTags,
  allLoras,
  onClose,
  onSave,
}: Props) {
  const isCreateMode = !character;
  const [name, setName] = useState(character?.name || ""); // Use optional chaining
  const [description, setDescription] = useState(character?.description || ""); // Use optional chaining
  const [gender, setGender] = useState<ActorGender>(character?.gender || "female"); // Use optional chaining
  const [customBasePrompt, setCustomBasePrompt] = useState(character?.custom_base_prompt || ""); // Use optional chaining
  const [customNegativePrompt, setCustomNegativePrompt] = useState(character?.custom_negative_prompt || ""); // Use optional chaining

  const [previewImageUrl, setPreviewImageUrl] = useState(character?.preview_image_url || ""); // Use optional chaining
  const [promptMode, setPromptMode] = useState<PromptMode>(character?.prompt_mode || "auto"); // Use optional chaining
  const [ipAdapterWeight, setIpAdapterWeight] = useState<number>(character?.ip_adapter_weight || 0.75); // Use optional chaining
  const [ipAdapterModel, setIpAdapterModel] = useState<string>(character?.ip_adapter_model || "clip_face"); // Use optional chaining

  // Tags state
  const [identityTagIds, setIdentityTagIds] = useState<number[]>(
    character?.tags?.filter(t => t.is_permanent).map(t => t.tag_id) || []
  );
  const [clothingTagIds, setClothingTagIds] = useState<number[]>(
    character?.tags?.filter(t => !t.is_permanent).map(t => t.tag_id) || []
  );
  const [tagSearch, setTagSearch] = useState("");
  const [activeTagInput, setActiveTagInput] = useState<"identity" | "clothing" | null>(null);

  // Raw Edit Mode State
  const [rawEditMode, setRawEditMode] = useState<"identity" | "clothing" | null>(null);
  const [rawEditText, setRawEditText] = useState("");

  // LoRAs state
  const [selectedLoras, setSelectedLoras] = useState<CharacterLoRA[]>(character?.loras || []);
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // Preview modal state
  const [previewImageOpen, setPreviewImageOpen] = useState(false);

  const handleGenerateReference = async () => {
    if (isCreateMode || !character?.id) return;

    setIsGenerating(true);
    try {
      const res = await axios.post(`${API_BASE}/characters/${character.id}/regenerate-reference`);
      if (res.data.url) {
        setPreviewImageUrl(res.data.url);
      }
    } catch (error) {
      console.error("Failed to generate reference", error);
      alert("Failed to generate reference image.");
    } finally {
      setIsGenerating(false);
    }
  };

  const [referenceBasePrompt, setReferenceBasePrompt] = useState(isCreateMode ? customBasePrompt : character?.reference_base_prompt || "");
  const [referenceNegativePrompt, setReferenceNegativePrompt] = useState(isCreateMode ? customNegativePrompt : character?.reference_negative_prompt || "");

  // Initialize prompt_mode if it exists in character object (it might be missing in older types, but we saw it in schema)
  useEffect(() => {
    if (character?.prompt_mode) { // Use optional chaining
      setPromptMode(character.prompt_mode);
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

  const toggleRawEdit = (type: "identity" | "clothing") => {
    if (rawEditMode === type) {
      // Save raw text
      const newTags = rawEditText
        .split(",")
        .map(t => t.trim())
        .filter(t => t.length > 0);

      const newIds: number[] = [];
      const notFound: string[] = [];

      newTags.forEach(tagName => {
        // Try strict match first
        let tag = allTags.find(t => t.name === tagName);
        // Try loose match (case insensitive) if not found
        if (!tag) {
          tag = allTags.find(t => t.name.toLowerCase() === tagName.toLowerCase());
        }

        if (tag) {
          if (!newIds.includes(tag.id)) {
            newIds.push(tag.id);
          }
        } else {
          notFound.push(tagName);
        }
      });

      if (notFound.length > 0) {
        alert(`Warning: The following tags were not found and will be ignored:\n${notFound.join(", ")}\n\nPlease use the Tag Manager to add new tags first.`);
      }

      if (type === "identity") {
        setIdentityTagIds(newIds);
      } else {
        setClothingTagIds(newIds);
      }
      setRawEditMode(null);
    } else {
      // Enter raw mode
      const tags = type === "identity" ? identityTags : clothingTags;
      setRawEditText(tags.map(t => t.name).join(", "));
      setRawEditMode(type);
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
    // Automatically sync raw edit text if user is still in raw edit mode
    let finalIdentityTagIds = identityTagIds;
    let finalClothingTagIds = clothingTagIds;

    if (rawEditMode) {
      const newTags = rawEditText
        .split(",")
        .map(t => t.trim())
        .filter(t => t.length > 0);

      const newIds: number[] = [];
      newTags.forEach(tagName => {
        const tag = allTags.find(t => t.name.toLowerCase() === tagName.toLowerCase());
        if (tag && !newIds.includes(tag.id)) {
          newIds.push(tag.id);
        }
      });

      if (rawEditMode === "identity") {
        finalIdentityTagIds = newIds;
        setIdentityTagIds(newIds);
      } else {
        finalClothingTagIds = newIds;
        setClothingTagIds(newIds);
      }
      setRawEditMode(null);
    }

    const payload = {
      name,
      description,
      gender,
      preview_image_url: previewImageUrl,
      tags: [
        ...finalIdentityTagIds.map(id => ({ tag_id: id, weight: 1.0, is_permanent: true })),
        ...finalClothingTagIds.map(id => ({ tag_id: id, weight: 1.0, is_permanent: false })),
      ],
      loras: selectedLoras,
      prompt_mode: promptMode,
      custom_base_prompt: customBasePrompt,
      custom_negative_prompt: customNegativePrompt,
      reference_base_prompt: referenceBasePrompt,
      reference_negative_prompt: referenceNegativePrompt,
      ip_adapter_weight: ipAdapterWeight,
      ip_adapter_model: ipAdapterModel,
    };

    console.log("💾 [CharacterEditModal] Saving character:", payload);
    setIsSaving(true);
    try {
      await onSave(payload, character?.id);
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
          <h2 className="text-lg font-bold text-zinc-900">
            {isCreateMode ? "Create New Character" : `Edit Character: ${character?.name}`}
          </h2>
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
            <div className="flex gap-2">
              <input
                value={previewImageUrl}
                readOnly
                className="flex-1 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-mono text-zinc-500 outline-none"
              />
              <button
                type="button"
                onClick={handleGenerateReference}
                disabled={isCreateMode || isGenerating}
                className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGenerating ? (
                  <>
                    <LoadingSpinner size="sm" color="text-zinc-400" />
                    <span>Generating...</span>
                  </>
                ) : (
                  "Generate"
                )}
              </button>
            </div>
            {isCreateMode && (
              <p className="text-[10px] text-zinc-400 mt-1">
                Save the character first to generate a reference image.
              </p>
            )}
            {previewImageUrl && (
              <div className="mt-3">
                <img
                  src={previewImageUrl}
                  alt="Character Preview"
                  onClick={() => setPreviewImageOpen(true)}
                  className="h-32 w-auto rounded-xl border-2 border-zinc-200 object-cover cursor-pointer hover:border-zinc-400 hover:shadow-lg transition-all"
                />
              </div>
            )}
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
              Auto: Automatically decides whether to use LoRA based on prompt complexity.<br />
              Standard: Forces standard generation.<br />
              LoRA: Forces usage of character LoRAs.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">IP-Adapter Settings</label>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-[10px] text-zinc-400 mb-1">Weight ({ipAdapterWeight})</label>
                <input
                  type="range"
                  min="0"
                  max="1.5"
                  step="0.05"
                  value={ipAdapterWeight}
                  onChange={(e) => setIpAdapterWeight(Number(e.target.value))}
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-[10px] text-zinc-400 mb-1">Model</label>
                <select
                  value={ipAdapterModel}
                  onChange={(e) => setIpAdapterModel(e.target.value)}
                  className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400 bg-white"
                >
                  <option value="clip_face">clip_face (Standard)</option>
                  <option value="clip">clip (Style/Chibi)</option>
                  <option value="faceid">faceid (Realistic)</option>
                </select>
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider">Base Prompt (Raw Text)</label>
                {!isCreateMode && (
                  <button
                    type="button"
                    onClick={() => setReferenceBasePrompt(customBasePrompt)}
                    className="text-[10px] text-zinc-500 hover:underline"
                  >
                    Copy to Ref.
                  </button>
                )}
              </div>
              <textarea
                value={customBasePrompt}
                onChange={(e) => setCustomBasePrompt(e.target.value)}
                rows={3}
                placeholder="Additional positive tags..."
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400 font-mono resize-none"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider">Base Negative (Raw Text)</label>
                {!isCreateMode && (
                  <button
                    type="button"
                    onClick={() => setReferenceNegativePrompt(customNegativePrompt)}
                    className="text-[10px] text-zinc-500 hover:underline"
                  >
                    Copy to Ref.
                  </button>
                )}
              </div>
              <textarea
                value={customNegativePrompt}
                onChange={(e) => setCustomNegativePrompt(e.target.value)}
                rows={3}
                placeholder="Additional negative tags..."
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400 font-mono resize-none"
              />
            </div>
          </div>


          {/* Identity Tags */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider">Identity Tags</label>
              <button
                onClick={() => toggleRawEdit("identity")}
                className="text-[10px] font-semibold text-zinc-500 hover:text-zinc-800 underline"
              >
                {rawEditMode === "identity" ? "Done" : "Edit as Text"}
              </button>
            </div>
            {rawEditMode === "identity" ? (
              <textarea
                value={rawEditText}
                onChange={(e) => setRawEditText(e.target.value)}
                rows={3}
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400 font-mono"
                placeholder="tag1, tag2, tag3..."
              />
            ) : (
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
            )}
          </div>

          {/* Clothing Tags */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider">Clothing Tags</label>
              <button
                onClick={() => toggleRawEdit("clothing")}
                className="text-[10px] font-semibold text-zinc-500 hover:text-zinc-800 underline"
              >
                {rawEditMode === "clothing" ? "Done" : "Edit as Text"}
              </button>
            </div>
            {rawEditMode === "clothing" ? (
              <textarea
                value={rawEditText}
                onChange={(e) => setRawEditText(e.target.value)}
                rows={3}
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400 font-mono"
                placeholder="tag1, tag2, tag3..."
              />
            ) : (
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
            )}
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

          {/* Reference Image Prompts */}
          <div className="border-t border-zinc-200 pt-6 mt-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
                <label className="block text-sm font-bold text-zinc-800 uppercase tracking-tight">Reference Image Generation</label>
                <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-[9px] font-bold text-indigo-500 uppercase">IP-Adapter Context</span>
              </div>
              <span className="text-[10px] text-zinc-400 font-medium bg-zinc-50 px-2 py-0.5 rounded-full border border-zinc-100">
                Determines the visual quality of the character profile image
              </span>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Reference Positive</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setReferenceBasePrompt("masterpiece, best_quality, ultra-detailed, solo, upper_body, portrait, facing_viewer, front_view, looking_at_viewer, straight_on, white_background, simple_background, plain_background, solid_background")}
                      className="text-[9px] text-indigo-600 hover:text-indigo-800 font-bold bg-indigo-50 hover:bg-indigo-100 px-1.5 py-0.5 rounded transition-colors"
                    >
                      RESET TO DEFAULT
                    </button>
                    {!isCreateMode && (
                      <button
                        type="button"
                        onClick={() => setReferenceBasePrompt(customBasePrompt)}
                        className="text-[9px] text-zinc-500 hover:text-zinc-700 font-bold bg-zinc-100 hover:bg-zinc-200 px-1.5 py-0.5 rounded transition-colors"
                      >
                        COPY FROM BASE
                      </button>
                    )}
                  </div>
                </div>
                <div className="relative group">
                  <textarea
                    value={referenceBasePrompt}
                    onChange={(e) => setReferenceBasePrompt(e.target.value)}
                    rows={4}
                    placeholder="masterpiece, best_quality, anime_portrait, looking_at_viewer..."
                    className="w-full rounded-2xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-[11px] outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50 font-mono resize-none transition-all"
                  />
                  <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-[9px] text-zinc-300 font-mono">Positive</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Reference Negative</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setReferenceNegativePrompt("lowres, (bad_anatomy:1.2), (bad_hands:1.2), text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, normal_quality, jpeg_artifacts, signature, watermark, username, blurry, easynegative, verybadimagenegative_v1.3, detailed_background, scenery, outdoors, indoors")}
                      className="text-[9px] text-indigo-600 hover:text-indigo-800 font-bold bg-indigo-50 hover:bg-indigo-100 px-1.5 py-0.5 rounded transition-colors"
                    >
                      RESET TO DEFAULT
                    </button>
                    {!isCreateMode && (
                      <button
                        type="button"
                        onClick={() => setReferenceNegativePrompt(customNegativePrompt)}
                        className="text-[9px] text-zinc-500 hover:text-zinc-700 font-bold bg-zinc-100 hover:bg-zinc-200 px-1.5 py-0.5 rounded transition-colors"
                      >
                        COPY FROM BASE
                      </button>
                    )}
                  </div>
                </div>
                <div className="relative group">
                  <textarea
                    value={referenceNegativePrompt}
                    onChange={(e) => setReferenceNegativePrompt(e.target.value)}
                    rows={4}
                    placeholder="easynegative, from_side, from_behind, profile..."
                    className="w-full rounded-2xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-[11px] outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50 font-mono resize-none transition-all"
                  />
                  <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-[9px] text-zinc-300 font-mono">Negative</span>
                  </div>
                </div>
              </div>
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

      {/* Image Preview Modal */}
      {previewImageOpen && (
        <ImagePreviewModal
          src={previewImageUrl}
          onClose={() => setPreviewImageOpen(false)}
        />
      )}
    </div>
  );
}
