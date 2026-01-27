"use client";

import { useState, useMemo, useEffect } from "react";
import axios from "axios";
import { Character, CharacterLoRA, Tag, LoRA, ActorGender, PromptMode } from "../types";
import { API_BASE } from "../constants";
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
  const [customBasePrompt, setCustomBasePrompt] = useState(character.custom_base_prompt || "");
  const [customNegativePrompt, setCustomNegativePrompt] = useState(character.custom_negative_prompt || "");
  const [referenceBasePrompt, setReferenceBasePrompt] = useState(character.reference_base_prompt || "");
  const [referenceNegativePrompt, setReferenceNegativePrompt] = useState(character.reference_negative_prompt || "");
  const [previewImageUrl, setPreviewImageUrl] = useState(character.preview_image_url || "");
  const [promptMode, setPromptMode] = useState<PromptMode>("auto"); // Default to auto if not present in type (it is in type now)
  const [ipAdapterWeight, setIpAdapterWeight] = useState<number>(character.ip_adapter_weight || 0.75);

  // Tag suggestion state
  const [suggestedIdentityTags, setSuggestedIdentityTags] = useState<Tag[]>([]);
  const [suggestedClothingTags, setSuggestedClothingTags] = useState<Tag[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [ipAdapterModel, setIpAdapterModel] = useState<string>(character.ip_adapter_model || "clip_face");

  // Tags state
  const [identityTagIds, setIdentityTagIds] = useState<number[]>(character.identity_tags || []);
  const [clothingTagIds, setClothingTagIds] = useState<number[]>(character.clothing_tags || []);
  const [tagSearch, setTagSearch] = useState("");
  const [activeTagInput, setActiveTagInput] = useState<"identity" | "clothing" | null>(null);
  
  // Raw Edit Mode State
  const [rawEditMode, setRawEditMode] = useState<"identity" | "clothing" | null>(null);
  const [rawEditText, setRawEditText] = useState("");

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

  const handleSuggestTags = async () => {
    if (!customBasePrompt.trim()) {
      setShowSuggestions(false);
      return;
    }

    setIsSuggesting(true);
    try {
      const response = await axios.post(`${API_BASE}/characters/suggest-tags`, {
        prompt: customBasePrompt,
      });

      const { identity_tags, clothing_tags } = response.data;
      setSuggestedIdentityTags(identity_tags);
      setSuggestedClothingTags(clothing_tags);
      setShowSuggestions(identity_tags.length > 0 || clothing_tags.length > 0);
    } catch (error) {
      console.error("Failed to suggest tags", error);
    } finally {
      setIsSuggesting(false);
    }
  };

  const handleAddAllSuggestions = () => {
    // Add suggested identity tags
    const newIdentityIds = suggestedIdentityTags
      .filter(tag => !identityTagIds.includes(tag.id))
      .map(tag => tag.id);
    setIdentityTagIds([...identityTagIds, ...newIdentityIds]);

    // Add suggested clothing tags
    const newClothingIds = suggestedClothingTags
      .filter(tag => !clothingTagIds.includes(tag.id))
      .map(tag => tag.id);
    setClothingTagIds([...clothingTagIds, ...newClothingIds]);

    // Close suggestions panel
    setShowSuggestions(false);
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
        custom_base_prompt: customBasePrompt,
        custom_negative_prompt: customNegativePrompt,
        reference_base_prompt: referenceBasePrompt,
        reference_negative_prompt: referenceNegativePrompt,
        ip_adapter_weight: ipAdapterWeight,
        ip_adapter_model: ipAdapterModel,
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
              <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Base Prompt (Raw Text)</label>
              <textarea
                value={customBasePrompt}
                onChange={(e) => setCustomBasePrompt(e.target.value)}
                onBlur={handleSuggestTags}
                rows={3}
                placeholder="Additional positive tags..."
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400 font-mono resize-none"
              />

              {/* Tag Suggestions Panel */}
              {isSuggesting && (
                <div className="mt-2 p-3 rounded-lg bg-blue-50 border border-blue-200">
                  <div className="flex items-center gap-2 text-sm text-blue-600">
                    <LoadingSpinner size={16} />
                    <span>Analyzing prompt...</span>
                  </div>
                </div>
              )}

              {showSuggestions && !isSuggesting && (
                <div className="mt-2 p-3 rounded-lg bg-green-50 border border-green-200">
                  <div className="flex items-start justify-between mb-2">
                    <div className="text-xs font-semibold text-green-700 uppercase">📋 Suggested Tags ({suggestedIdentityTags.length + suggestedClothingTags.length} found)</div>
                    <button
                      onClick={() => setShowSuggestions(false)}
                      className="text-green-600 hover:text-green-800 text-xs"
                    >
                      ✕
                    </button>
                  </div>

                  {suggestedIdentityTags.length > 0 && (
                    <div className="mb-2">
                      <div className="text-xs font-medium text-green-600 mb-1">Identity:</div>
                      <div className="flex flex-wrap gap-1">
                        {suggestedIdentityTags.map(tag => (
                          <span key={tag.id} className="px-2 py-1 bg-white rounded text-xs text-green-700 border border-green-300">
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {suggestedClothingTags.length > 0 && (
                    <div className="mb-2">
                      <div className="text-xs font-medium text-green-600 mb-1">Clothing:</div>
                      <div className="flex flex-wrap gap-1">
                        {suggestedClothingTags.map(tag => (
                          <span key={tag.id} className="px-2 py-1 bg-white rounded text-xs text-green-700 border border-green-300">
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={handleAddAllSuggestions}
                      className="px-3 py-1 bg-green-600 text-white text-xs rounded-lg hover:bg-green-700 transition-colors"
                    >
                      Add All
                    </button>
                    <button
                      onClick={() => setShowSuggestions(false)}
                      className="px-3 py-1 bg-white text-green-600 text-xs rounded-lg border border-green-300 hover:bg-green-50 transition-colors"
                    >
                      Ignore
                    </button>
                  </div>
                </div>
              )}
            </div>
            <div>
              <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Base Negative (Raw Text)</label>
              <textarea
                value={customNegativePrompt}
                onChange={(e) => setCustomNegativePrompt(e.target.value)}
                rows={3}
                placeholder="Additional negative tags..."
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400 font-mono resize-none"
              />
            </div>
          </div>

          {/* Reference Image Prompts */}
          <div className="border-t border-zinc-200 pt-4">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider">Reference Image Generation</label>
              <span className="text-[10px] text-zinc-400">For IP-Adapter reference creation</span>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold text-zinc-400 mb-1">Reference Positive</label>
                <textarea
                  value={referenceBasePrompt}
                  onChange={(e) => setReferenceBasePrompt(e.target.value)}
                  rows={3}
                  placeholder="masterpiece, best quality, anime portrait, looking at viewer..."
                  className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-xs outline-none focus:border-zinc-400 font-mono resize-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-zinc-400 mb-1">Reference Negative</label>
                <textarea
                  value={referenceNegativePrompt}
                  onChange={(e) => setReferenceNegativePrompt(e.target.value)}
                  rows={3}
                  placeholder="easynegative, from side, from behind, profile..."
                  className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-xs outline-none focus:border-zinc-400 font-mono resize-none"
                />
              </div>
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
