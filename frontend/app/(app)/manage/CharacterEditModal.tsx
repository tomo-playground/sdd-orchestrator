"use client";

import React from "react";
import { useCharacterForm } from "./hooks/useCharacterForm";
import PreviewImageSection from "./PreviewImageSection";
import CharacterTagsEditor from "./CharacterTagsEditor";
import ReferencePromptsPanel from "./ReferencePromptsPanel";
import GeminiPreviewEditModal from "./GeminiPreviewEditModal";
import ImagePreviewModal from "../../components/ui/ImagePreviewModal";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import { Character, Tag, LoRA, ActorGender, PromptMode, VoicePreset } from "../../types";

type Props = {
  character?: Character;
  allTags: Tag[];
  allLoras: LoRA[];
  onClose: () => void;
  onSave: (data: Partial<Character>, id?: number) => Promise<void>;
};

export default function CharacterEditModal({
  character,
  allTags,
  allLoras,
  onClose,
  onSave,
}: Props) {
  const form = useCharacterForm(character, allTags, allLoras, onSave, onClose);

  return (
    <div className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center overflow-y-auto bg-black/50 p-4 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-3xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-100 bg-zinc-50/50 px-6 py-4">
          <h2 className="text-lg font-bold text-zinc-900">
            {form.isCreateMode ? "Create New Character" : `Edit Character: ${character?.name}`}
          </h2>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-600"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="h-5 w-5"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {/* Basic Info + Preview Image side by side */}
          <div className="flex gap-4">
            <div className="min-w-0 flex-1 space-y-3">
              <BasicInfoSection
                name={form.name}
                setName={form.setName}
                gender={form.gender}
                setGender={form.setGender}
                description={form.description}
                setDescription={form.setDescription}
              />
            </div>
            <div className="shrink-0">
              <PreviewImageSection
                isCreateMode={form.isCreateMode}
                previewImageUrl={form.previewImageUrl}
                previewLocked={form.previewLocked}
                setPreviewLocked={form.setPreviewLocked}
                isGenerating={form.isGenerating}
                isEnhancing={form.isEnhancing}
                isEditing={form.isEditing}
                onGenerate={form.handleGenerateReference}
                onEnhance={form.handleEnhancePreview}
                onOpenGeminiEdit={() => form.setGeminiEditOpen(true)}
                onOpenPreview={() => form.setPreviewImageOpen(true)}
              />
            </div>
          </div>

          {/* Prompt Mode */}
          <PromptModeSection promptMode={form.promptMode} setPromptMode={form.setPromptMode} />

          {/* IP-Adapter Settings */}
          <IpAdapterSection
            ipAdapterWeight={form.ipAdapterWeight}
            setIpAdapterWeight={form.setIpAdapterWeight}
            ipAdapterModel={form.ipAdapterModel}
            setIpAdapterModel={form.setIpAdapterModel}
          />

          {/* Voice Preset */}
          <VoicePresetSection
            voicePresets={form.voicePresets}
            selectedId={form.defaultVoicePresetId}
            onChange={form.setDefaultVoicePresetId}
          />

          {/* Scene Identity + Common Negative */}
          <SceneIdentitySection
            isCreateMode={form.isCreateMode}
            customBasePrompt={form.customBasePrompt}
            setCustomBasePrompt={form.setCustomBasePrompt}
            customNegativePrompt={form.customNegativePrompt}
            setCustomNegativePrompt={form.setCustomNegativePrompt}
            setReferenceBasePrompt={form.setReferenceBasePrompt}
            setReferenceNegativePrompt={form.setReferenceNegativePrompt}
            sceneIdentityWarning={form.sceneIdentityWarning}
          />

          {/* Tags */}
          <CharacterTagsEditor
            identityTags={form.identityTags}
            clothingTags={form.clothingTags}
            filteredTags={form.filteredTags}
            tagSearch={form.tagSearch}
            setTagSearch={form.setTagSearch}
            activeTagInput={form.activeTagInput}
            setActiveTagInput={form.setActiveTagInput}
            rawEditMode={form.rawEditMode}
            rawEditText={form.rawEditText}
            setRawEditText={form.setRawEditText}
            onAddTag={form.handleAddTag}
            onRemoveTag={form.handleRemoveTag}
            onToggleRawEdit={form.toggleRawEdit}
          />

          {/* LoRAs */}
          <LoRAsSection
            selectedLoras={form.selectedLoras}
            allLoras={allLoras}
            onAddLora={form.handleAddLora}
            onUpdateLora={form.handleUpdateLora}
            onRemoveLora={form.handleRemoveLora}
          />

          {/* Reference Prompts */}
          <ReferencePromptsPanel
            isCreateMode={form.isCreateMode}
            referenceBasePrompt={form.referenceBasePrompt}
            setReferenceBasePrompt={form.setReferenceBasePrompt}
            referenceNegativePrompt={form.referenceNegativePrompt}
            setReferenceNegativePrompt={form.setReferenceNegativePrompt}
            customBasePrompt={form.customBasePrompt}
            customNegativePrompt={form.customNegativePrompt}
            referenceProfileWarning={form.referenceProfileWarning}
          />
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 border-t border-zinc-100 bg-zinc-50/50 px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-50"
            disabled={form.isSaving}
          >
            Cancel
          </button>
          <button
            onClick={form.handleSubmit}
            disabled={form.isSaving}
            className="flex items-center gap-2 rounded-full bg-zinc-900 px-6 py-2 text-xs font-semibold text-white hover:bg-zinc-800 disabled:opacity-50"
          >
            {form.isSaving && <LoadingSpinner size="sm" color="text-white/50" />}
            {form.isSaving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>

      {/* Image Preview Modal */}
      {form.previewImageOpen && (
        <ImagePreviewModal
          src={form.previewImageUrl}
          onClose={() => form.setPreviewImageOpen(false)}
        />
      )}

      {/* Gemini Edit Modal */}
      {form.geminiEditOpen && (
        <GeminiPreviewEditModal
          previewImageUrl={form.previewImageUrl}
          geminiTargetChange={form.geminiTargetChange}
          setGeminiTargetChange={form.setGeminiTargetChange}
          onClose={() => form.setGeminiEditOpen(false)}
          onSubmit={form.handleEditPreview}
        />
      )}
    </div>
  );
}
// --- Inline sections (layout-only, not worth separate files) ---
function BasicInfoSection({
  name,
  setName,
  gender,
  setGender,
  description,
  setDescription,
}: {
  name: string;
  setName: (v: string) => void;
  gender: ActorGender;
  setGender: (v: ActorGender) => void;
  description: string;
  setDescription: (v: string) => void;
}) {
  return (
    <>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
            Name
          </label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
            Gender
          </label>
          <select
            value={gender || "female"}
            onChange={(e) => setGender(e.target.value as ActorGender)}
            className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
          >
            <option value="female">Female</option>
            <option value="male">Male</option>
          </select>
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
          Description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="w-full resize-none rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-zinc-400"
        />
      </div>
    </>
  );
}
function PromptModeSection({
  promptMode,
  setPromptMode,
}: {
  promptMode: PromptMode;
  setPromptMode: (v: PromptMode) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
        Prompt Mode
      </label>
      <select
        value={promptMode}
        onChange={(e) => setPromptMode(e.target.value as PromptMode)}
        className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
      >
        <option value="auto">Auto (Smart Compose)</option>
        <option value="standard">Standard (No LoRA)</option>
        <option value="lora">LoRA Only</option>
      </select>
      <p className="mt-1 text-[10px] text-zinc-400">
        Auto: Smart compose. Standard: No LoRA. LoRA: Forces character LoRAs.
      </p>
    </div>
  );
}
function IpAdapterSection({
  ipAdapterWeight,
  setIpAdapterWeight,
  ipAdapterModel,
  setIpAdapterModel,
}: {
  ipAdapterWeight: number;
  setIpAdapterWeight: (v: number) => void;
  ipAdapterModel: string;
  setIpAdapterModel: (v: string) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
        IP-Adapter Settings
      </label>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-[10px] text-zinc-400">Weight ({ipAdapterWeight})</label>
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
          <label className="mb-1 block text-[10px] text-zinc-400">Model</label>
          <select
            value={ipAdapterModel}
            onChange={(e) => setIpAdapterModel(e.target.value)}
            className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
          >
            <option value="clip_face">clip_face (Standard)</option>
            <option value="clip">clip (Style/Chibi)</option>
            <option value="faceid">faceid (Realistic)</option>
          </select>
        </div>
      </div>
    </div>
  );
}
function SceneIdentitySection({
  isCreateMode,
  customBasePrompt,
  setCustomBasePrompt,
  customNegativePrompt,
  setCustomNegativePrompt,
  setReferenceBasePrompt,
  setReferenceNegativePrompt,
  sceneIdentityWarning,
}: {
  isCreateMode: boolean;
  customBasePrompt: string;
  setCustomBasePrompt: React.Dispatch<React.SetStateAction<string>>;
  customNegativePrompt: string;
  setCustomNegativePrompt: (v: string) => void;
  setReferenceBasePrompt: (v: string) => void;
  setReferenceNegativePrompt: (v: string) => void;
  sceneIdentityWarning: string | null;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <div className="mb-1 flex items-center justify-between">
          <label className="block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
            Scene Identity (Fixed Appearance)
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() =>
                setCustomBasePrompt((prev) => {
                  const base = "masterpiece, best_quality";
                  if (!prev.includes(base)) return `${base}, ${prev}`.trim().replace(/^,\s+/, "");
                  return prev;
                })
              }
              className="rounded bg-zinc-100 px-1.5 py-0.5 text-[9px] font-bold text-zinc-500 transition-colors hover:bg-zinc-200 hover:text-zinc-700"
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
          className={`w-full rounded-xl border ${sceneIdentityWarning ? "border-amber-400" : "border-zinc-200"} resize-none px-3 py-2 font-mono text-sm outline-none focus:border-zinc-400`}
        />
        {sceneIdentityWarning && (
          <p className="mt-1 text-[10px] font-medium text-amber-600 italic">
            {sceneIdentityWarning}
          </p>
        )}
      </div>
      <div>
        <div className="mb-1 flex items-center justify-between">
          <label className="block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
            Common Negative (Scene)
          </label>
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
          className="w-full resize-none rounded-xl border border-zinc-200 px-3 py-2 font-mono text-sm outline-none focus:border-zinc-400"
        />
      </div>
    </div>
  );
}
function LoRAsSection({
  selectedLoras,
  allLoras,
  onAddLora,
  onUpdateLora,
  onRemoveLora,
}: {
  selectedLoras: { lora_id: number; weight: number }[];
  allLoras: LoRA[];
  onAddLora: () => void;
  onUpdateLora: (index: number, field: "lora_id" | "weight", value: number) => void;
  onRemoveLora: (index: number) => void;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <label className="block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
          LoRAs
        </label>
        <button
          onClick={onAddLora}
          className="rounded-full bg-indigo-50 px-2 py-1 text-[10px] font-semibold text-indigo-600 hover:text-indigo-700"
        >
          + Add LoRA
        </button>
      </div>
      <div className="space-y-2">
        {selectedLoras.map((lora, index) => (
          <div
            key={index}
            className="flex items-center gap-2 rounded-xl border border-zinc-100 bg-zinc-50/50 p-2"
          >
            <select
              value={lora.lora_id}
              onChange={(e) => onUpdateLora(index, "lora_id", Number(e.target.value))}
              className="flex-1 rounded-lg border border-zinc-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-zinc-400"
            >
              {allLoras.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.display_name || l.name}
                </option>
              ))}
            </select>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={lora.weight}
              onChange={(e) => onUpdateLora(index, "weight", Number(e.target.value))}
              className="w-16 rounded-lg border border-zinc-200 px-2 py-1.5 text-center text-xs outline-none focus:border-zinc-400"
            />
            <button
              onClick={() => onRemoveLora(index)}
              className="px-1 text-rose-400 hover:text-rose-600"
            >
              x
            </button>
          </div>
        ))}
        {selectedLoras.length === 0 && (
          <p className="text-xs text-zinc-400 italic">No LoRAs assigned.</p>
        )}
      </div>
    </div>
  );
}
function VoicePresetSection({
  voicePresets,
  selectedId,
  onChange,
}: {
  voicePresets: VoicePreset[];
  selectedId: number | null;
  onChange: (id: number | null) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
        Default Voice Preset
      </label>
      <select
        value={selectedId ?? ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
      >
        <option value="">None (use render panel default)</option>
        {voicePresets.map((vp) => (
          <option key={vp.id} value={vp.id}>
            {vp.name}
            {vp.description ? ` — ${vp.description}` : ""}
          </option>
        ))}
      </select>
      <p className="mt-1 text-[10px] text-zinc-400">
        Assigned voice for this character. Overrides the global render preset voice during TTS.
      </p>
    </div>
  );
}
