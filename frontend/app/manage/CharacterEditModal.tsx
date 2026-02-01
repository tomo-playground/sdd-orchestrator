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
  const [previewLocked, setPreviewLocked] = useState(character?.preview_locked ?? false);
  const [promptMode, setPromptMode] = useState<PromptMode>(character?.prompt_mode || "auto"); // Use optional chaining
  const [ipAdapterWeight, setIpAdapterWeight] = useState<number>(character?.ip_adapter_weight || 0.75); // Use optional chaining
  const [ipAdapterModel, setIpAdapterModel] = useState<string>(character?.ip_adapter_model || "clip_face"); // Use optional chaining

  const [referenceBasePrompt, setReferenceBasePrompt] = useState(isCreateMode ? customBasePrompt : character?.reference_base_prompt || "");
  const [referenceNegativePrompt, setReferenceNegativePrompt] = useState(isCreateMode ? customNegativePrompt : character?.reference_negative_prompt || "");

  // Linting warnings
  const restrictedKeywords = ["background", "kitchen", "room", "outdoors", "indoors", "scenery", "nature", "mountain", "street", "office", "bedroom", "bathroom", "garden"];
  const sceneIdentityWarning = useMemo(() => {
    const tokens = customBasePrompt.toLowerCase().split(/[,\s]+/).map(t => t.trim());
    const found = tokens.filter(t => restrictedKeywords.includes(t));
    return found.length > 0 ? `Warning: Background tags detected (${found.join(", ")}). Please remove them for better consistency.` : null;
  }, [customBasePrompt]);

  const referenceProfileWarning = useMemo(() => {
    const lower = referenceBasePrompt.toLowerCase();
    if (!lower.includes("white background") && !lower.includes("simple background") && !lower.includes("plain background")) {
      return "Tip: Adding 'white background' is recommended for cleaner character reference.";
    }
    return null;
  }, [referenceBasePrompt]);

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
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [geminiEditOpen, setGeminiEditOpen] = useState(false);
  const [geminiTargetChange, setGeminiTargetChange] = useState("");

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

  const handleEnhancePreview = async () => {
    if (isCreateMode || !character?.id || !previewImageUrl) return;
    if (!confirm("Enhance preview image with Gemini? (~$0.04 cost)")) return;

    setIsEnhancing(true);
    try {
      const res = await axios.post(`${API_BASE}/characters/${character.id}/enhance-preview`);
      if (res.data.url) {
        setPreviewImageUrl(res.data.url);
      }
    } catch (error) {
      console.error("Failed to enhance preview", error);
      alert("Failed to enhance preview image.");
    } finally {
      setIsEnhancing(false);
    }
  };

  const handleEditPreview = async (instruction: string) => {
    if (isCreateMode || !character?.id || !previewImageUrl || !instruction.trim()) return;

    setIsEditing(true);
    setGeminiEditOpen(false);
    try {
      const res = await axios.post(`${API_BASE}/characters/${character.id}/edit-preview`, {
        instruction: instruction.trim(),
      });
      if (res.data.url) {
        setPreviewImageUrl(res.data.url);
        setGeminiTargetChange("");
      }
    } catch (error) {
      console.error("Failed to edit preview", error);
      alert("Failed to edit preview image.");
    } finally {
      setIsEditing(false);
    }
  };

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
      // preview_image_url removed - now read-only via backend @property
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
      preview_locked: previewLocked,
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
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="w-full max-w-2xl bg-white rounded-3xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-100 flex justify-between items-center bg-zinc-50/50">
          <h2 className="text-lg font-bold text-zinc-900">
            {isCreateMode ? "Create New Character" : `Edit Character: ${character?.name}`}
          </h2>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
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
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider">Preview Image</label>
              {previewImageUrl && (
                <button
                  type="button"
                  onClick={() => setPreviewLocked(!previewLocked)}
                  className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-semibold transition ${
                    previewLocked
                      ? "bg-amber-100 text-amber-700 border border-amber-300"
                      : "bg-zinc-100 text-zinc-500 border border-zinc-200 hover:bg-zinc-200"
                  }`}
                >
                  {previewLocked ? "Locked" : "Unlocked"}
                </button>
              )}
            </div>
            <div className="flex gap-2">
              <input
                value={previewImageUrl}
                readOnly
                className="flex-1 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-mono text-zinc-500 outline-none"
              />
              <button
                type="button"
                onClick={handleGenerateReference}
                disabled={isCreateMode || previewLocked || isGenerating || isEnhancing || isEditing}
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
              <button
                type="button"
                onClick={handleEnhancePreview}
                disabled={isCreateMode || previewLocked || !previewImageUrl || isEnhancing || isGenerating || isEditing}
                className="flex items-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2 text-xs font-semibold text-indigo-600 hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isEnhancing ? (
                  <>
                    <LoadingSpinner size="sm" color="text-indigo-400" />
                    <span>Enhancing...</span>
                  </>
                ) : (
                  "Enhance"
                )}
              </button>
            </div>
            {isCreateMode && (
              <p className="text-[10px] text-zinc-400 mt-1">
                Save the character first to generate a reference image.
              </p>
            )}
            {previewImageUrl && (
              <div className="mt-3 flex items-center gap-3">
                <div className="relative">
                  <img
                    src={previewImageUrl}
                    alt="Character Preview"
                    onClick={() => setPreviewImageOpen(true)}
                    className={`h-32 w-auto rounded-xl border-2 object-cover cursor-pointer hover:shadow-lg transition-all ${
                      previewLocked ? "border-amber-300" : "border-zinc-200 hover:border-zinc-400"
                    }`}
                  />
                  {previewLocked && (
                    <div className="absolute top-1 right-1 rounded-full bg-amber-500 p-1">
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="white" className="w-3 h-3">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                      </svg>
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => setGeminiEditOpen(true)}
                  disabled={isCreateMode || previewLocked || isEditing || isGenerating || isEnhancing}
                  className="flex items-center gap-2 rounded-xl border border-purple-200 bg-gradient-to-r from-purple-50 to-pink-50 px-4 py-2 text-xs font-semibold text-purple-600 hover:from-purple-100 hover:to-pink-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isEditing ? (
                    <>
                      <LoadingSpinner size="sm" color="text-purple-400" />
                      <span>Editing...</span>
                    </>
                  ) : (
                    "Edit with Gemini"
                  )}
                </button>
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
                <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider">Scene Identity (Fixed Appearance)</label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setCustomBasePrompt(prev => {
                      const base = "masterpiece, best_quality";
                      if (!prev.includes(base)) return `${base}, ${prev}`.trim().replace(/^,\s+/, "");
                      return prev;
                    })}
                    className="text-[9px] text-zinc-500 hover:text-zinc-700 font-bold bg-zinc-100 hover:bg-zinc-200 px-1.5 py-0.5 rounded transition-colors"
                  >
                    + QUALITY
                  </button>
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
              </div>
              <textarea
                value={customBasePrompt}
                onChange={(e) => setCustomBasePrompt(e.target.value)}
                rows={3}
                placeholder="Tags that define character's core look (e.g. hair style, eye color, unique traits). NO BACKGROUND TAGS."
                className={`w-full rounded-xl border ${sceneIdentityWarning ? 'border-amber-400' : 'border-zinc-200'} px-3 py-2 text-sm outline-none focus:border-zinc-400 font-mono resize-none`}
              />
              {sceneIdentityWarning && (
                <p className="text-[10px] text-amber-600 mt-1 font-medium italic">⚠️ {sceneIdentityWarning}</p>
              )}
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider">Common Negative (Scene)</label>
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
                  <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Reference Positive (Studio Profile)</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setReferenceBasePrompt(prev => {
                        const studio = "full_body, (standing:1.2), white_background, simple_background, solo, straight_on, facing_viewer";
                        let updated = prev;
                        if (!updated.includes("masterpiece")) updated = `masterpiece, best_quality, ${updated}`;
                        if (!updated.includes("white_background")) updated = `${updated}, ${studio}`;
                        return updated.replace(/,\s*,/g, ",").replace(/^,\s+/, "").trim();
                      })}
                      className="text-[9px] text-indigo-600 hover:text-indigo-800 font-bold bg-indigo-50 hover:bg-indigo-100 px-1.5 py-0.5 rounded transition-colors"
                    >
                      SET STUDIO SETUP
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
                    className={`w-full rounded-2xl border ${referenceProfileWarning ? 'border-indigo-200' : 'border-zinc-200'} bg-zinc-50/50 px-4 py-3 text-[11px] outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50 font-mono resize-none transition-all`}
                  />
                  {referenceProfileWarning && (
                    <p className="text-[10px] text-indigo-500 mt-1 font-medium italic">💡 {referenceProfileWarning}</p>
                  )}
                  <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-[9px] text-zinc-300 font-mono">Positive</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Reference Negative (Studio Profile)</label>
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

      {/* Gemini Edit Modal */}
      {geminiEditOpen && (
        <div className="fixed inset-0 z-[1100] flex items-center justify-center bg-black/50">
          <div className="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-zinc-800">Edit with Gemini</h3>
              <button
                type="button"
                onClick={() => { setGeminiEditOpen(false); setGeminiTargetChange(""); }}
                className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
              >
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              {previewImageUrl && (
                <div className="flex justify-center">
                  <img src={previewImageUrl} alt="Current Preview" className="h-40 w-auto rounded-xl border border-zinc-200 object-cover" />
                </div>
              )}

              <div>
                <label className="mb-2 block text-sm font-semibold text-zinc-700">
                  How would you like to change this image?
                </label>
                <div className="mb-2 flex flex-wrap gap-2">
                  {[
                    "Smile brightly, looking at viewer",
                    "Sitting on chair with hands on lap",
                    "Turn around, looking over shoulder",
                    "Wave hand with cheerful expression",
                    "Close-up face portrait",
                    "Standing with arms crossed",
                  ].map((example) => (
                    <button
                      key={example}
                      type="button"
                      onClick={() => setGeminiTargetChange(example)}
                      className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs text-zinc-600 transition hover:border-purple-300 hover:bg-purple-50"
                    >
                      {example}
                    </button>
                  ))}
                </div>
                <textarea
                  value={geminiTargetChange}
                  onChange={(e) => setGeminiTargetChange(e.target.value)}
                  placeholder="Describe the change in natural language..."
                  className="w-full rounded-xl border border-zinc-200 bg-white/80 px-4 py-3 text-sm outline-none focus:border-purple-400"
                  rows={3}
                />
              </div>

              <div className="flex justify-between gap-3">
                <button
                  type="button"
                  onClick={() => { setGeminiEditOpen(false); setGeminiTargetChange(""); }}
                  className="flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (!geminiTargetChange.trim()) {
                      alert("Please describe what to change.");
                      return;
                    }
                    handleEditPreview(geminiTargetChange.trim());
                  }}
                  disabled={!geminiTargetChange.trim()}
                  className="flex-1 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:from-purple-600 hover:to-pink-600 disabled:cursor-not-allowed disabled:from-purple-300 disabled:to-pink-300"
                >
                  Start Editing (~$0.04)
                </button>
              </div>

              <p className="text-[10px] text-zinc-400">
                Gemini preserves face and art style while editing pose, expression, and gaze.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
