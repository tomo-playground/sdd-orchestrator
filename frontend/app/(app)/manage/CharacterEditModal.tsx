"use client";

import React, { useEffect } from "react";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import { useCharacterForm } from "./hooks/useCharacterForm";
import PreviewImageSection from "./PreviewImageSection";
import CharacterTagsEditor from "./CharacterTagsEditor";
import ReferencePromptsPanel from "./ReferencePromptsPanel";
import GeminiPreviewEditModal from "./GeminiPreviewEditModal";
import {
  BasicInfoSection,
  PromptModeSection,
  IpAdapterSection,
  SceneIdentitySection,
  LoRAsSection,
  VoicePresetSection,
} from "./sections/CharacterFormSections";
import ImagePreviewModal from "../../components/ui/ImagePreviewModal";
import ConfirmDialog, { useConfirm } from "../../components/ui/ConfirmDialog";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import { useUIStore } from "../../store/useUIStore";
import { Character, Tag, LoRA } from "../../types";

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
  const trapRef = useFocusTrap(true);
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();
  const form = useCharacterForm({
    character,
    allTags,
    allLoras,
    onSave,
    onClose,
    showToast,
    confirmDialog: confirm,
  });

  // Escape key to close (guard: skip when inner modals are open)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key === "Escape" &&
        !form.geminiEditOpen &&
        !form.previewImageOpen &&
        !dialogProps.open
      ) {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, form.geminiEditOpen, form.previewImageOpen, dialogProps.open]);

  return (
    <div
      className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center overflow-y-auto bg-black/50 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="character-edit-title"
    >
      <div
        ref={trapRef}
        tabIndex={-1}
        className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-3xl bg-white shadow-2xl outline-none"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-100 bg-zinc-50/50 px-6 py-4">
          <h2 id="character-edit-title" className="text-lg font-bold text-zinc-900">
            {form.isCreateMode ? "Create New Character" : `Edit Character: ${character?.name}`}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
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

          <PromptModeSection promptMode={form.promptMode} setPromptMode={form.setPromptMode} />

          <IpAdapterSection
            ipAdapterWeight={form.ipAdapterWeight}
            setIpAdapterWeight={form.setIpAdapterWeight}
            ipAdapterModel={form.ipAdapterModel}
            setIpAdapterModel={form.setIpAdapterModel}
          />

          <VoicePresetSection
            voicePresets={form.voicePresets}
            selectedId={form.defaultVoicePresetId}
            onChange={form.setDefaultVoicePresetId}
          />

          <SceneIdentitySection
            isCreateMode={form.isCreateMode}
            customBasePrompt={form.customBasePrompt}
            setCustomBasePrompt={form.setCustomBasePrompt}
            customNegativePrompt={form.customNegativePrompt}
            setCustomNegativePrompt={form.setCustomNegativePrompt}
            onCopyToReference={(type) => {
              if (type === "base") form.setReferenceBasePrompt(form.customBasePrompt);
              else form.setReferenceNegativePrompt(form.customNegativePrompt);
            }}
            sceneIdentityWarning={form.sceneIdentityWarning}
          />

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

          <LoRAsSection
            selectedLoras={form.selectedLoras}
            allLoras={form.localLoras}
            onAddLora={form.handleAddLora}
            onUpdateLora={form.handleUpdateLora}
            onRemoveLora={form.handleRemoveLora}
            onLoraTypeChange={form.handleLoraTypeChange}
          />

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

      {form.previewImageOpen && (
        <ImagePreviewModal
          src={form.previewImageUrl}
          onClose={() => form.setPreviewImageOpen(false)}
        />
      )}

      {form.geminiEditOpen && (
        <GeminiPreviewEditModal
          previewImageUrl={form.previewImageUrl}
          geminiTargetChange={form.geminiTargetChange}
          setGeminiTargetChange={form.setGeminiTargetChange}
          onClose={() => form.setGeminiEditOpen(false)}
          onSubmit={form.handleEditPreview}
        />
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
