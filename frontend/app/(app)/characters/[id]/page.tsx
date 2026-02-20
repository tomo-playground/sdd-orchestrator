"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RefreshCw, Trash2, UserRound } from "lucide-react";
import { resolveImageUrl } from "../../../utils/url";
import { CONTAINER_CLASSES } from "../../../components/ui/variants";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import Button from "../../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import ImagePreviewModal from "../../../components/ui/ImagePreviewModal";
import { BasicInfoSection, PromptsSection, SectionCard } from "./CharacterDetailSections";
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
  } = useCharacterEdit(rawId);

  const isLoading = isCharLoading || isTagDataLoading;

  const onDelete = async () => {
    if (!character) return;
    const ok = await confirm({
      title: "Delete Character",
      message: `"${character.name}" will be moved to trash.`,
      confirmLabel: "Delete",
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
        <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
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
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRegenerate}
            loading={isRegenerating}
            disabled={isRegenerating}
            className="w-full"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            {isRegenerating ? "Generating..." : "Regenerate Preview"}
          </Button>
        </div>

        {/* Right: Detail sections */}
        <div className="space-y-4">
          <BasicInfoSection form={form} onChange={updateField} />

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
      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
