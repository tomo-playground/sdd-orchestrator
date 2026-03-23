"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Copy, RefreshCw, Trash2, UserRound } from "lucide-react";
import { resolveImageUrl } from "../../../../utils/url";
import { CONTAINER_CLASSES } from "../../../../components/ui/variants";
import LoadingSpinner from "../../../../components/ui/LoadingSpinner";
import Button from "../../../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../../../components/ui/ConfirmDialog";
import ImagePreviewModal from "../../../../components/ui/ImagePreviewModal";
import {
  BasicInfoSection,
  PromptsSection,
  VoicePresetSection,
  IpAdapterSection,
  SectionCard,
} from "./CharacterDetailSections";
import DuplicateDialog from "./DuplicateDialog";
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
  const [duplicateOpen, setDuplicateOpen] = useState(false);

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
    groups,
    currentStyleName,
    styleLoraIds,
    isCharLoading,
    isSaving,
    selectedTags,
    selectedLoras,
    isDirty,
    updateField,
    handleGroupChange,
    handleToggleTag,
    handleSearchTagSelect,
    handleToggleLora,
    handleUpdateLoraWeight,
    handleSave,
    handleDelete,
    handleRegenerate,
    isRegenerating,
  } = useCharacterEdit(rawId);

  const isLoading = isCharLoading || isTagDataLoading;
  const isBusy = isRegenerating;

  const onDelete = async () => {
    if (!character) return;
    const ok = await confirm({
      title: "캐릭터 삭제",
      message: (
        <>
          <span className="font-semibold text-zinc-900">{character.name}</span>을(를) 휴지통으로
          이동합니다.
        </>
      ),
      confirmLabel: "삭제",
      variant: "danger",
    });
    if (ok) await handleDelete();
  };

  if (isLoading || !character || !form) {
    return (
      <div className={`${CONTAINER_CLASSES} flex items-center justify-center py-32`}>
        <LoadingSpinner size="md" />
      </div>
    );
  }

  const imgSrc = resolveImageUrl(character.reference_image_url);

  return (
    <div className={`${CONTAINER_CLASSES} py-6`}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/library/characters"
            className="flex items-center gap-1 text-xs font-medium text-zinc-400 hover:text-zinc-600"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Characters
          </Link>
          <span className="text-zinc-300">/</span>
          <h1 className="text-lg font-bold text-zinc-900">{character.name}</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setDuplicateOpen(true)}>
            <Copy className="h-3.5 w-3.5" />
            Duplicate
          </Button>
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

      {/* Two-column layout — responsive: stack on small, side-by-side on lg+ */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
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
                <p className="mt-2 text-xs text-zinc-400">프리뷰 없음</p>
              </div>
            )}
            {isBusy && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                <LoadingSpinner size="md" />
              </div>
            )}
          </div>

          {/* Preview action buttons */}
          <div className="grid grid-cols-1 gap-1.5">
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
          </div>
        </div>

        {/* Right: Detail sections */}
        <div className="space-y-4">
          <BasicInfoSection
            form={form}
            onChange={updateField}
            groups={groups}
            onGroupChange={handleGroupChange}
            currentStyleName={currentStyleName}
          />

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
              excludeLoraIds={styleLoraIds}
              onToggleLora={handleToggleLora}
              onUpdateWeight={handleUpdateLoraWeight}
            />
          </SectionCard>

          <SectionCard title="Prompts" collapsible defaultOpen={false}>
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
      {duplicateOpen && (
        <DuplicateDialog
          character={character}
          groups={groups}
          onClose={() => setDuplicateOpen(false)}
        />
      )}
      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
