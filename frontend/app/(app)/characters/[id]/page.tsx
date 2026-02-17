"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { ArrowLeft, Trash2, UserRound } from "lucide-react";
import { API_BASE } from "../../../constants";
import { useCharacters } from "../../../hooks/useCharacters";
import { useUIStore } from "../../../store/useUIStore";
import { resolveImageUrl } from "../../../utils/url";
import { getErrorMsg } from "../../../utils/error";
import { CONTAINER_CLASSES } from "../../../components/ui/variants";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import Button from "../../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import ImagePreviewModal from "../../../components/ui/ImagePreviewModal";
import type { CharacterFull, CharacterTagLink, Tag } from "../../../types";
import {
  BasicInfoSection,
  PromptsSection,
  type CharacterFormData,
} from "./CharacterDetailSections";
import AppearanceStep, { type WizardTag } from "../builder/steps/AppearanceStep";
import LoraStep from "../builder/steps/LoraStep";
import type { WizardLoRA } from "../builder/wizardReducer";
import { WIZARD_CATEGORIES, type WizardCategory } from "../builder/wizardTemplates";
import { useTagData } from "../shared/useTagData";
import { applyTagToggle, applyFreeTagToggle } from "../shared/tagUtils";

// ── Conversion helpers ──────────────────────────────────────

function tagsToWizard(tags: CharacterTagLink[]): WizardTag[] {
  return tags.map((t) => ({
    tagId: t.tag_id,
    name: t.name ?? `#${t.tag_id}`,
    groupName: t.group_name ?? "identity",
    isPermanent: t.is_permanent,
  }));
}

function lorasToWizard(loras: { lora_id: number; weight: number }[]): WizardLoRA[] {
  return loras.map((lr) => ({ loraId: lr.lora_id, weight: lr.weight }));
}

function formFromCharacter(ch: CharacterFull): CharacterFormData {
  return {
    name: ch.name,
    description: ch.description ?? "",
    gender: ch.gender,
    prompt_mode: ch.prompt_mode,
    custom_base_prompt: ch.custom_base_prompt ?? "",
    custom_negative_prompt: ch.custom_negative_prompt ?? "",
    reference_base_prompt: ch.reference_base_prompt ?? "",
    reference_negative_prompt: ch.reference_negative_prompt ?? "",
  };
}

// ── Page component ───────────────────────────────────────────
export default function CharacterDetailPage() {
  const params = useParams();
  const router = useRouter();
  const rawId = Number(params.id);
  const showToast = useUIStore((s) => s.showToast);
  const { getCharacterFull } = useCharacters();
  const { confirm, dialogProps } = useConfirm();

  const [character, setCharacter] = useState<CharacterFull | null>(null);
  const [form, setForm] = useState<CharacterFormData | null>(null);
  const [isCharLoading, setIsCharLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);

  // Tag/LoRA editing state
  const [selectedTags, setSelectedTags] = useState<WizardTag[]>([]);
  const [selectedLoras, setSelectedLoras] = useState<WizardLoRA[]>([]);
  const [initialTags, setInitialTags] = useState<WizardTag[]>([]);
  const [initialLoras, setInitialLoras] = useState<WizardLoRA[]>([]);

  // Shared tag/LoRA data + search
  const {
    tagsByGroup,
    allLoras,
    isLoading: isTagDataLoading,
    searchQuery,
    setSearchQuery,
    searchResults,
  } = useTagData();

  const isLoading = isCharLoading || isTagDataLoading;

  // ── Load character ─────────────────────────────────────────
  useEffect(() => {
    (async () => {
      const ch = await getCharacterFull(rawId);
      if (!ch) {
        showToast("Character not found", "error");
        router.replace("/library?tab=characters");
        return;
      }
      setCharacter(ch);
      setForm(formFromCharacter(ch));

      const wizTags = tagsToWizard(ch.tags ?? []);
      // Backend loras field has lora_id (CharacterLoRA schema)
      const rawLoras = (ch.loras ?? []) as unknown as { lora_id: number; weight: number }[];
      const wizLoras = lorasToWizard(rawLoras);
      setSelectedTags(wizTags);
      setSelectedLoras(wizLoras);
      setInitialTags(wizTags);
      setInitialLoras(wizLoras);

      setIsCharLoading(false);
    })();
  }, [rawId, getCharacterFull, showToast, router]);

  // ── Form updater ───────────────────────────────────────────
  const updateField = useCallback(
    <K extends keyof CharacterFormData>(key: K, value: CharacterFormData[K]) => {
      setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
    },
    []
  );

  // ── Tag handlers ──────────────────────────────────────────
  const handleToggleTag = useCallback((tag: Tag, category: WizardCategory) => {
    const wizTag: WizardTag = {
      tagId: tag.id,
      name: tag.name,
      groupName: category.groupName,
      isPermanent: category.isPermanent,
    };
    setSelectedTags((prev) => applyTagToggle(prev, wizTag, category));
  }, []);

  const handleSearchTagSelect = useCallback(
    (tag: Tag) => {
      const category = WIZARD_CATEGORIES.find((c) => c.groupName === tag.group_name);
      if (category) {
        handleToggleTag(tag, category);
      } else {
        const wizTag: WizardTag = {
          tagId: tag.id,
          name: tag.name,
          groupName: tag.group_name ?? "identity",
          isPermanent: true,
        };
        setSelectedTags((prev) => applyFreeTagToggle(prev, wizTag));
      }
    },
    [handleToggleTag],
  );

  // ── LoRA handlers ─────────────────────────────────────────
  const handleToggleLora = useCallback((loraId: number, defaultWeight: number) => {
    setSelectedLoras((prev) => {
      const exists = prev.some((l) => l.loraId === loraId);
      if (exists) return prev.filter((l) => l.loraId !== loraId);
      return [...prev, { loraId, weight: defaultWeight }];
    });
  }, []);

  const handleUpdateLoraWeight = useCallback((loraId: number, weight: number) => {
    setSelectedLoras((prev) => prev.map((l) => (l.loraId === loraId ? { ...l, weight } : l)));
  }, []);

  // ── Save ───────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    if (!form || !character) return;
    if (form.name.trim().length < 2) {
      showToast("Name must be at least 2 characters", "warning");
      return;
    }
    setIsSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim() || null,
        gender: form.gender,
        prompt_mode: form.prompt_mode,
        custom_base_prompt: form.custom_base_prompt.trim() || null,
        custom_negative_prompt: form.custom_negative_prompt.trim() || null,
        reference_base_prompt: form.reference_base_prompt.trim() || null,
        reference_negative_prompt: form.reference_negative_prompt.trim() || null,
        tags: selectedTags.map((t) => ({
          tag_id: t.tagId,
          weight: 1.0,
          is_permanent: t.isPermanent,
        })),
        loras: selectedLoras.map((l) => ({
          lora_id: l.loraId,
          weight: l.weight,
        })),
      };
      const res = await axios.put(`${API_BASE}/characters/${character.id}`, payload);
      setCharacter(res.data);
      setForm(formFromCharacter(res.data));

      const wizTags = tagsToWizard(res.data.tags ?? []);
      const rawLoras = (res.data.loras ?? []) as unknown as { lora_id: number; weight: number }[];
      const wizLoras = lorasToWizard(rawLoras);
      setSelectedTags(wizTags);
      setSelectedLoras(wizLoras);
      setInitialTags(wizTags);
      setInitialLoras(wizLoras);

      showToast("Character saved", "success");
    } catch (err) {
      showToast(getErrorMsg(err, "Failed to save"), "error");
    } finally {
      setIsSaving(false);
    }
  }, [form, character, selectedTags, selectedLoras, showToast]);

  // ── Delete ─────────────────────────────────────────────────
  const handleDelete = useCallback(async () => {
    if (!character) return;
    const ok = await confirm({
      title: "Delete Character",
      message: `"${character.name}" will be moved to trash.`,
      confirmLabel: "Delete",
      variant: "danger",
    });
    if (!ok) return;
    try {
      await axios.delete(`${API_BASE}/characters/${character.id}`);
      showToast("Character deleted", "success");
      router.push("/library?tab=characters");
    } catch (err) {
      showToast(getErrorMsg(err, "Failed to delete"), "error");
    }
  }, [character, confirm, showToast, router]);

  // ── Dirty check ────────────────────────────────────────────
  const tagsChanged = useMemo(() => {
    if (selectedTags.length !== initialTags.length) return true;
    const initialIds = new Set(initialTags.map((t) => t.tagId));
    return selectedTags.some((t) => !initialIds.has(t.tagId));
  }, [selectedTags, initialTags]);

  const lorasChanged = useMemo(() => {
    if (selectedLoras.length !== initialLoras.length) return true;
    return selectedLoras.some((l) => {
      const orig = initialLoras.find((o) => o.loraId === l.loraId);
      return !orig || orig.weight !== l.weight;
    });
  }, [selectedLoras, initialLoras]);

  const isDirty =
    form && character
      ? form.name !== character.name ||
        form.description !== (character.description ?? "") ||
        form.gender !== character.gender ||
        form.prompt_mode !== character.prompt_mode ||
        form.custom_base_prompt !== (character.custom_base_prompt ?? "") ||
        form.custom_negative_prompt !== (character.custom_negative_prompt ?? "") ||
        form.reference_base_prompt !== (character.reference_base_prompt ?? "") ||
        form.reference_negative_prompt !== (character.reference_negative_prompt ?? "") ||
        tagsChanged ||
        lorasChanged
      : false;

  // ── Loading state ──────────────────────────────────────────
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
          <Button variant="ghost" size="sm" onClick={handleDelete}>
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

        </div>

        {/* Right: Detail sections */}
        <div className="space-y-4">
          <BasicInfoSection form={form} onChange={updateField} />

          {/* Appearance (Tag Picker) */}
          <div className="rounded-2xl border border-zinc-200/60 bg-white p-5">
            <p className="mb-4 text-[12px] font-semibold tracking-wider text-zinc-500 uppercase">
              Appearance
            </p>
            <AppearanceStep
              tagsByGroup={tagsByGroup}
              selectedTags={selectedTags}
              onToggleTag={handleToggleTag}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              searchResults={searchResults}
              onSearchTagSelect={handleSearchTagSelect}
            />
          </div>

          {/* LoRA Selection */}
          <div className="rounded-2xl border border-zinc-200/60 bg-white p-5">
            <LoraStep
              allLoras={allLoras}
              selectedLoras={selectedLoras}
              gender={form.gender ?? "female"}
              onToggleLora={handleToggleLora}
              onUpdateWeight={handleUpdateLoraWeight}
            />
          </div>

          <PromptsSection form={form} onChange={updateField} />
        </div>
      </div>

      {/* Modals */}
      {previewOpen && <ImagePreviewModal src={imgSrc} onClose={() => setPreviewOpen(false)} />}
      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
