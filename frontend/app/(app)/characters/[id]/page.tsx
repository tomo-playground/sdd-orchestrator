"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Palette, Pencil, RefreshCw, Sparkles, Trash2, UserRound } from "lucide-react";
import { resolveImageUrl } from "../../../utils/url";
import { CONTAINER_CLASSES } from "../../../components/ui/variants";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import Button from "../../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import ImagePreviewModal from "../../../components/ui/ImagePreviewModal";
import {
  BasicInfoSection,
  PromptsSection,
  VoicePresetSection,
  IpAdapterSection,
  SectionCard,
} from "./CharacterDetailSections";
import GeminiEditModal from "./GeminiEditModal";
import AppearanceStep from "../builder/steps/AppearanceStep";
import LoraStep from "../builder/steps/LoraStep";
import { useTagData } from "../shared/useTagData";
import { formatTagName } from "../shared/formatTag";
import { useCharacterEdit } from "./useCharacterEdit";

export default function CharacterDetailPage() {
  const params = useParams();
  const rawId = Number(params.id);
  const { confirm, dialogProps } = useConfirm();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [geminiEditOpen, setGeminiEditOpen] = useState(false);

  const {
    tagsByGroup,
    allLoras,
    isLoading: isTagDataLoading,
    searchQuery,
    setSearchQuery,
    searchResults,
  } = useTagData();

  const {
    character,
    form,
    isCharLoading,
    isSaving,
    selectedTags,
    selectedLoras,
    isDirty,
    updateField,
    handleToggleTag,
    handleSearchTagSelect,
    handleToggleLora,
    handleUpdateLoraWeight,
    handleSave,
    handleDelete,
    handleRegenerate,
    isRegenerating,
    handleEnhance,
    isEnhancing,
    handleEditPreview,
    isEditingPreview,
  } = useCharacterEdit(rawId);

  const isLoading = isCharLoading || isTagDataLoading;
  const isBusy = isRegenerating || isEnhancing || isEditingPreview;

  const onDelete = async () => {
    if (!character) return;
    const ok = await confirm({
      title: "Delete Character",
      message: (
        <>
          <span className="font-semibold text-zinc-900">{character.name}</span>을(를)
          휴지통으로 이동합니다.
        </>
      ),
      confirmLabel: "Delete",
      variant: "danger",
    });
    if (ok) await handleDelete();
  };

  const onEnhance = async () => {
    const ok = await confirm({
      title: "Enhance Preview",
      message: "Gemini로 프리뷰 이미지를 보정합니다. (~$0.04)",
      confirmLabel: "Enhance",
    });
    if (ok) await handleEnhance();
  };

  if (isLoading || !character || !form) {
    return (
      <div className={`${CONTAINER_CLASSES} flex items-center justify-center py-32`}>
        <LoadingSpinner size="md" />
      </div>
    );
  }

  const imgSrc = resolveImageUrl(character.preview_image_url);

  return (
    <div className={`${CONTAINER_CLASSES} py-6`}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/library?tab=characters"
            className="flex items-center gap-1 text-xs font-medium text-zinc-400 hover:text-zinc-600"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Characters
          </Link>
          <span className="text-zinc-300">/</span>
          <h1 className="text-lg font-bold text-zinc-900">{character.name}</h1>
          {character.style_profile_name && (
            <span className="flex items-center gap-1 rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-500">
              <Palette className="h-3 w-3" />
              {character.style_profile_name}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={onDelete}>
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSave}
            loading={isSaving}
            disabled={!isDirty || isSaving}
          >
            Save Changes
          </Button>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Left: Preview panel */}
        <div className="space-y-3 lg:sticky lg:top-4 lg:self-start">
          <div
            className="relative flex aspect-[3/4] cursor-pointer items-center justify-center overflow-hidden rounded-2xl border border-zinc-200 bg-zinc-50"
            onClick={() => imgSrc && setPreviewOpen(true)}
          >
            {imgSrc ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img src={imgSrc} alt={character.name} className="h-full w-full object-cover" />
            ) : (
              <div className="text-center">
                <UserRound className="mx-auto h-12 w-12 text-zinc-300" />
                <p className="mt-2 text-xs text-zinc-400">No preview</p>
              </div>
            )}
            {isBusy && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                <LoadingSpinner size="md" />
              </div>
            )}
          </div>

          {/* Preview action buttons */}
          <div className="grid grid-cols-3 gap-1.5">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleRegenerate}
              disabled={isBusy}
              className="w-full text-[12px]"
              title="SD로 프리뷰 재생성"
            >
              <RefreshCw className={`h-3 w-3 ${isRegenerating ? "animate-spin" : ""}`} />
              Regen
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={onEnhance}
              disabled={isBusy || !imgSrc}
              className="w-full text-[12px]"
              title="Gemini로 품질 보정"
            >
              <Sparkles className={`h-3 w-3 ${isEnhancing ? "animate-pulse" : ""}`} />
              Enhance
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setGeminiEditOpen(true)}
              disabled={isBusy || !imgSrc}
              className="w-full text-[12px]"
              title="Gemini 자연어 편집"
            >
              <Pencil className={`h-3 w-3 ${isEditingPreview ? "animate-pulse" : ""}`} />
              Edit
            </Button>
          </div>
        </div>

        {/* Right: Detail sections */}
        <div className="space-y-4">
          <BasicInfoSection form={form} onChange={updateField} />

          <SectionCard
            title="Voice"
            collapsible
            defaultOpen={false}
            summary={form.voice_preset_id ? `Preset #${form.voice_preset_id}` : undefined}
          >
            <VoicePresetSection form={form} onChange={updateField} />
          </SectionCard>

          <SectionCard
            title="IP-Adapter"
            collapsible
            defaultOpen={false}
            summary={`${form.ip_adapter_model} (${form.ip_adapter_weight})`}
          >
            <IpAdapterSection form={form} onChange={updateField} />
          </SectionCard>

          <SectionCard
            title="Appearance"
            collapsible
            defaultOpen={false}
            summary={
              selectedTags.length > 0
                ? `${selectedTags.length} tags (${selectedTags
                    .slice(0, 3)
                    .map((t) => formatTagName(t.name))
                    .join(", ")}${selectedTags.length > 3 ? ", ..." : ""})`
                : undefined
            }
          >
            <AppearanceStep
              tagsByGroup={tagsByGroup}
              selectedTags={selectedTags}
              onToggleTag={handleToggleTag}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              searchResults={searchResults}
              onSearchTagSelect={handleSearchTagSelect}
            />
          </SectionCard>

          <SectionCard
            title="LoRA"
            collapsible
            defaultOpen={false}
            summary={
              selectedLoras.length > 0 ? `${selectedLoras.length} LoRAs selected` : undefined
            }
          >
            <LoraStep
              allLoras={allLoras}
              selectedLoras={selectedLoras}
              gender={form.gender ?? "female"}
              onToggleLora={handleToggleLora}
              onUpdateWeight={handleUpdateLoraWeight}
            />
          </SectionCard>

          <SectionCard
            title="Prompts"
            collapsible
            defaultOpen={false}
            summary={`Mode: ${form.prompt_mode}`}
          >
            <PromptsSection
              form={form}
              onChange={updateField}
              selectedTagNames={selectedTags.map((t) => t.name)}
            />
          </SectionCard>
        </div>
      </div>

      {/* Modals */}
      {previewOpen && <ImagePreviewModal src={imgSrc} onClose={() => setPreviewOpen(false)} />}
      {geminiEditOpen && (
        <GeminiEditModal
          previewImageUrl={imgSrc ?? undefined}
          isProcessing={isEditingPreview}
          currentPrompt={form?.custom_base_prompt || ""}
          characterId={rawId}
          onClose={() => setGeminiEditOpen(false)}
          onSubmit={(instruction) => {
            void handleEditPreview(instruction);
            setGeminiEditOpen(false);
          }}
          onApplyPromptEdit={(edited) => updateField("custom_base_prompt", edited)}
        />
      )}
      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
