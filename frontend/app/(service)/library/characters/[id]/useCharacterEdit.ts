import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { API_BASE } from "../../../../constants";
import { useCharacters } from "../../../../hooks/useCharacters";
import { useUIStore } from "../../../../store/useUIStore";
import { getErrorMsg } from "../../../../utils/error";
import type { CharacterFull, GroupItem, Tag } from "../../../../types";
import type { WizardTag } from "../builder/steps/AppearanceStep";
import type { WizardLoRA } from "../builder/wizardReducer";
import type { WizardCategory } from "../builder/wizardTemplates";
import { WIZARD_CATEGORIES } from "../builder/wizardTemplates";
import { applyTagToggle, applyFreeTagToggle } from "../shared/tagUtils";
import type { CharacterFormData } from "./CharacterDetailSections";

// ── Conversion helpers ──────────────────────────────────────

function tagsToWizard(
  tags: { tag_id: number; name?: string; group_name?: string; is_permanent: boolean }[]
): WizardTag[] {
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
    group_id: ch.group_id,
    positive_prompt: ch.positive_prompt ?? "",
    negative_prompt: ch.negative_prompt ?? "",
    voice_preset_id: ch.voice_preset_id ?? null,
    ip_adapter_weight: ch.ip_adapter_weight ?? 0.35,
    ip_adapter_model: ch.ip_adapter_model ?? "clip_face",
    ip_adapter_guidance_start: ch.ip_adapter_guidance_start ?? null,
    ip_adapter_guidance_end: ch.ip_adapter_guidance_end ?? null,
  };
}

export function useCharacterEdit(rawId: number) {
  const router = useRouter();
  const showToast = useUIStore((s) => s.showToast);
  const { getCharacterFull } = useCharacters();

  const [character, setCharacter] = useState<CharacterFull | null>(null);
  const [form, setForm] = useState<CharacterFormData | null>(null);
  const [isCharLoading, setIsCharLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [isEditingPreview, setIsEditingPreview] = useState(false);

  // Groups for series dropdown
  const [groups, setGroups] = useState<GroupItem[]>([]);

  // Tag/LoRA editing state
  const [selectedTags, setSelectedTags] = useState<WizardTag[]>([]);
  const [selectedLoras, setSelectedLoras] = useState<WizardLoRA[]>([]);
  const [initialTags, setInitialTags] = useState<WizardTag[]>([]);
  const [initialLoras, setInitialLoras] = useState<WizardLoRA[]>([]);

  // ── Load groups ────────────────────────────────────────────
  useEffect(() => {
    axios
      .get<GroupItem[]>(`${API_BASE}/groups`)
      .then((res) => setGroups(res.data))
      .catch(() => {});
  }, []);

  // ── Load character ─────────────────────────────────────────
  useEffect(() => {
    (async () => {
      const ch = await getCharacterFull(rawId);
      if (!ch) {
        showToast("캐릭터를 찾을 수 없습니다", "error");
        router.replace("/library/characters");
        return;
      }
      setCharacter(ch);
      setForm(formFromCharacter(ch));

      const wizTags = tagsToWizard(ch.tags ?? []);
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
    [handleToggleTag]
  );

  // ── LoRA handlers ─────────────────────────────────────────
  const handleToggleLora = useCallback((loraId: number, defaultWeight: number) => {
    setSelectedLoras((prev) => {
      const exists = prev.some((l) => l.loraId === loraId);
      if (exists) return prev.filter((l) => l.loraId !== loraId);
      // Single-select: replace previous character LoRA
      return [{ loraId, weight: defaultWeight }];
    });
  }, []);

  const handleUpdateLoraWeight = useCallback((loraId: number, weight: number) => {
    setSelectedLoras((prev) => prev.map((l) => (l.loraId === loraId ? { ...l, weight } : l)));
  }, []);

  // ── Group change ────────────────────────────────────────────
  const handleGroupChange = useCallback((newGroupId: number) => {
    setForm((prev) => (prev ? { ...prev, group_id: newGroupId } : prev));
  }, []);

  // Derive current style profile name from groups + form.group_id
  const currentStyleName = useMemo(() => {
    if (!form?.group_id || groups.length === 0) return character?.style_profile_name ?? null;
    const g = groups.find((g) => g.id === form.group_id);
    return g?.style_profile_name ?? character?.style_profile_name ?? null;
  }, [form?.group_id, groups, character?.style_profile_name]);

  // ── StyleProfile LoRA exclusion ──────────────────────────
  const [styleLoraIds, setStyleLoraIds] = useState<number[]>([]);

  useEffect(() => {
    if (!form?.group_id || groups.length === 0) return;
    const g = groups.find((g) => g.id === form.group_id);
    const spId = g?.style_profile_id;
    if (!spId) {
      setStyleLoraIds([]);
      return;
    }
    axios
      .get(`${API_BASE}/style-profiles/${spId}/full`)
      .then((res) => {
        const loras: { id: number }[] = res.data.loras ?? [];
        setStyleLoraIds(loras.map((l) => l.id));
      })
      .catch(() => setStyleLoraIds([]));
  }, [form?.group_id, groups]);

  // ── Save ───────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    if (!form || !character) return;
    if (form.name.trim().length < 2) {
      showToast("이름은 2자 이상이어야 합니다", "warning");
      return;
    }
    setIsSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim() || null,
        gender: form.gender,
        group_id: form.group_id,
        positive_prompt: form.positive_prompt.trim() || null,
        negative_prompt: form.negative_prompt.trim() || null,
        voice_preset_id: form.voice_preset_id,
        ip_adapter_weight: form.ip_adapter_weight,
        ip_adapter_model: form.ip_adapter_model,
        ip_adapter_guidance_start: form.ip_adapter_guidance_start,
        ip_adapter_guidance_end: form.ip_adapter_guidance_end,
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

      showToast("캐릭터 저장 완료", "success");
    } catch (err) {
      showToast(getErrorMsg(err, "캐릭터 저장에 실패했습니다"), "error");
    } finally {
      setIsSaving(false);
    }
  }, [form, character, selectedTags, selectedLoras, showToast]);

  // ── Delete ─────────────────────────────────────────────────
  const handleDelete = useCallback(async () => {
    if (!character) return false;
    try {
      await axios.delete(`${API_BASE}/characters/${character.id}`);
      showToast("캐릭터 삭제 완료", "success");
      router.push("/library/characters");
      return true;
    } catch (err) {
      showToast(getErrorMsg(err, "캐릭터 삭제에 실패했습니다"), "error");
      return false;
    }
  }, [character, showToast, router]);

  // ── Regenerate preview ─────────────────────────────────────
  const handleRegenerate = useCallback(async () => {
    if (!character) return;
    setIsRegenerating(true);
    try {
      const res = await axios.post<{ ok: boolean; url?: string }>(
        `${API_BASE}/characters/${character.id}/regenerate-reference`
      );
      if (res.data.ok && res.data.url) {
        setCharacter((prev) =>
          prev ? { ...prev, reference_image_url: res.data.url ?? null } : prev
        );
        showToast("프리뷰 재생성 완료", "success");
      }
    } catch (err) {
      showToast(getErrorMsg(err, "프리뷰 재생성에 실패했습니다"), "error");
    } finally {
      setIsRegenerating(false);
    }
  }, [character, showToast]);

  // ── Enhance preview (Gemini) ──────────────────────────────
  const handleEnhance = useCallback(async () => {
    if (!character) return;
    setIsEnhancing(true);
    try {
      const res = await axios.post<{ ok?: boolean; url?: string }>(
        `${API_BASE}/characters/${character.id}/enhance-preview`
      );
      if (res.data.url) {
        setCharacter((prev) =>
          prev ? { ...prev, reference_image_url: res.data.url ?? null } : prev
        );
        showToast("프리뷰 향상 완료", "success");
      }
    } catch (err) {
      showToast(getErrorMsg(err, "프리뷰 향상에 실패했습니다"), "error");
    } finally {
      setIsEnhancing(false);
    }
  }, [character, showToast]);

  // ── Edit preview (Gemini instruction) ─────────────────────
  const handleEditPreview = useCallback(
    async (instruction: string) => {
      if (!character || !instruction.trim()) return;
      setIsEditingPreview(true);
      try {
        const res = await axios.post<{ ok?: boolean; url?: string }>(
          `${API_BASE}/characters/${character.id}/edit-preview`,
          { instruction: instruction.trim() }
        );
        if (res.data.url) {
          setCharacter((prev) =>
            prev ? { ...prev, reference_image_url: res.data.url ?? null } : prev
          );
          showToast("프리뷰 편집 완료", "success");
        }
      } catch (err) {
        showToast(getErrorMsg(err, "프리뷰 편집에 실패했습니다"), "error");
      } finally {
        setIsEditingPreview(false);
      }
    },
    [character, showToast]
  );

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
        form.group_id !== character.group_id ||
        form.positive_prompt !== (character.positive_prompt ?? "") ||
        form.negative_prompt !== (character.negative_prompt ?? "") ||
        form.voice_preset_id !== (character.voice_preset_id ?? null) ||
        form.ip_adapter_weight !== (character.ip_adapter_weight ?? 0.35) ||
        form.ip_adapter_model !== (character.ip_adapter_model ?? "clip_face") ||
        form.ip_adapter_guidance_start !== (character.ip_adapter_guidance_start ?? null) ||
        form.ip_adapter_guidance_end !== (character.ip_adapter_guidance_end ?? null) ||
        tagsChanged ||
        lorasChanged
      : false;

  return {
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
    handleEnhance,
    isEnhancing,
    handleEditPreview,
    isEditingPreview,
  };
}
