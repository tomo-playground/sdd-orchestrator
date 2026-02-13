"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { ArrowLeft } from "lucide-react";
import { API_BASE } from "../../../constants";
import { useUIStore } from "../../../store/useUIStore";
import { useCharacterForm } from "../../manage/hooks/useCharacterForm";
import PreviewImageSection from "../../manage/PreviewImageSection";
import CharacterTagsEditor from "../../manage/CharacterTagsEditor";
import ReferencePromptsPanel from "../../manage/ReferencePromptsPanel";
import GeminiPreviewEditModal from "../../manage/GeminiPreviewEditModal";
import {
  BasicInfoSection,
  PromptModeSection,
  IpAdapterSection,
  SceneIdentitySection,
  LoRAsSection,
  VoicePresetSection,
} from "../../manage/sections/CharacterFormSections";
import ImagePreviewModal from "../../../components/ui/ImagePreviewModal";
import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import Button from "../../../components/ui/Button";
import { CONTAINER_CLASSES } from "../../../components/ui/variants";
import type { Character, Tag, LoRA } from "../../../types";

export default function CharacterDetailPage() {
  const params = useParams();
  const router = useRouter();
  const showToast = useUIStore((s) => s.showToast);

  const rawId = params.id as string;

  const [character, setCharacter] = useState<Character | undefined>(undefined);
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [allLoras, setAllLoras] = useState<LoRA[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const [tagsRes, lorasRes, charRes] = await Promise.all([
          axios.get(`${API_BASE}/tags`),
          axios.get(`${API_BASE}/loras`),
          axios.get(`${API_BASE}/characters/${rawId}`),
        ]);
        setAllTags(tagsRes.data);
        setAllLoras(lorasRes.data);
        setCharacter(charRes.data);
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          showToast("Character not found or deleted", "error");
          router.push("/library?tab=characters");
          return;
        }
        showToast("Failed to load character data", "error");
      } finally {
        setIsLoaded(true);
      }
    };
    load();
  }, [rawId, showToast, router]);

  const handleSave = useCallback(
    async (data: Partial<Character>, id?: number) => {
      if (id) {
        await axios.put(`${API_BASE}/characters/${id}`, data);
        const res = await axios.get(`${API_BASE}/characters/${id}`);
        setCharacter(res.data);
        showToast("Character saved", "success");
      } else {
        const res = await axios.post(`${API_BASE}/characters`, data);
        showToast("Character created", "success");
        router.push(`/characters/${res.data.id}`);
      }
    },
    [showToast, router]
  );

  if (!isLoaded) {
    return (
      <div className={`${CONTAINER_CLASSES} flex items-center justify-center py-32`}>
        <LoadingSpinner size="md" />
      </div>
    );
  }

  if (!character) {
    return (
      <div className={`${CONTAINER_CLASSES} py-16 text-center`}>
        <p className="text-sm text-zinc-500">Character not found</p>
        <Link
          href="/library?tab=characters"
          className="mt-2 inline-block text-xs text-zinc-400 hover:underline"
        >
          Back to Characters
        </Link>
      </div>
    );
  }

  return (
    <CharacterDetailForm
      character={character}
      allTags={allTags}
      allLoras={allLoras}
      isNew={false}
      onSave={handleSave}
    />
  );
}

/** Inner form — only mounts after data is loaded so useState gets correct initial values */
export function CharacterDetailForm({
  character,
  allTags,
  allLoras,
  isNew,
  onSave,
}: {
  character: Character | undefined;
  allTags: Tag[];
  allLoras: LoRA[];
  isNew: boolean;
  onSave: (data: Partial<Character>, id?: number) => Promise<void>;
}) {
  const router = useRouter();
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();

  const form = useCharacterForm({
    character,
    allTags,
    allLoras,
    onSave,
    showToast,
    confirmDialog: confirm,
  });

  // --- beforeunload guard ---
  useEffect(() => {
    if (!form.isDirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [form.isDirty]);

  const handleBack = async () => {
    if (form.isDirty) {
      const ok = await confirm({
        title: "Unsaved Changes",
        message: "You have unsaved changes. Leave without saving?",
        confirmLabel: "Leave",
      });
      if (!ok) return;
    }
    router.push("/library?tab=characters");
  };

  const handleDelete = async () => {
    if (!character?.id) return;
    const ok = await confirm({
      title: "Delete Character",
      message: `Delete "${character.name}"? This action cannot be undone.`,
      confirmLabel: "Delete",
      variant: "danger",
    });
    if (!ok) return;
    try {
      await axios.delete(`${API_BASE}/characters/${character.id}`);
      showToast("Character deleted", "success");
      router.push("/library?tab=characters");
    } catch {
      showToast("Failed to delete character", "error");
    }
  };

  return (
    <div className={`${CONTAINER_CLASSES} py-6`}>
      {/* Back link + Title */}
      <div className="mb-6 flex items-center gap-3">
        <button
          onClick={handleBack}
          className="flex items-center gap-1 text-xs font-medium text-zinc-500 hover:text-zinc-700"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Characters
        </button>
        <h1 className="text-lg font-bold text-zinc-900">
          {isNew ? "Create New Character" : `Edit: ${character?.name}`}
        </h1>
      </div>

      {/* Two-column layout */}
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Left: Sticky side panel */}
        <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
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

        {/* Right: Scrollable form sections */}
        <div className="space-y-6">
          <section className="rounded-2xl border border-zinc-200/60 bg-white p-5">
            <div className="space-y-3">
              <BasicInfoSection
                name={form.name}
                setName={form.setName}
                gender={form.gender}
                setGender={form.setGender}
                description={form.description}
                setDescription={form.setDescription}
              />
            </div>
          </section>

          <section className="rounded-2xl border border-zinc-200/60 bg-white p-5">
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
          </section>

          <section className="rounded-2xl border border-zinc-200/60 bg-white p-5">
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
          </section>

          <section className="rounded-2xl border border-zinc-200/60 bg-white p-5">
            <LoRAsSection
              selectedLoras={form.selectedLoras}
              allLoras={form.localLoras}
              onAddLora={form.handleAddLora}
              onUpdateLora={form.handleUpdateLora}
              onRemoveLora={form.handleRemoveLora}
              onLoraTypeChange={form.handleLoraTypeChange}
            />
          </section>

          <section className="rounded-2xl border border-zinc-200/60 bg-white p-5">
            <PromptModeSection promptMode={form.promptMode} setPromptMode={form.setPromptMode} />
          </section>

          <section className="rounded-2xl border border-zinc-200/60 bg-white p-5">
            <IpAdapterSection
              ipAdapterWeight={form.ipAdapterWeight}
              setIpAdapterWeight={form.setIpAdapterWeight}
              ipAdapterModel={form.ipAdapterModel}
              setIpAdapterModel={form.setIpAdapterModel}
            />
          </section>

          <section className="rounded-2xl border border-zinc-200/60 bg-white p-5">
            <VoicePresetSection
              voicePresets={form.voicePresets}
              selectedId={form.defaultVoicePresetId}
              onChange={form.setDefaultVoicePresetId}
            />
          </section>

          <section className="rounded-2xl border border-zinc-200/60 bg-white p-5">
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
          </section>
        </div>
      </div>

      {/* Sticky bottom action bar */}
      <div className="sticky bottom-0 z-10 -mx-6 mt-6 border-t border-zinc-200 bg-white/95 px-6 py-3 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div>
            {form.isDirty && <span className="text-xs text-amber-500">Unsaved changes</span>}
          </div>
          <div className="flex items-center gap-2">
            {!isNew && (
              <Button variant="danger" size="sm" onClick={handleDelete}>
                Delete
              </Button>
            )}
            <Button size="sm" onClick={form.handleSubmit} loading={form.isSaving}>
              {form.isSaving ? "Saving..." : isNew ? "Create Character" : "Save Changes"}
            </Button>
          </div>
        </div>
      </div>

      {/* Modals */}
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
