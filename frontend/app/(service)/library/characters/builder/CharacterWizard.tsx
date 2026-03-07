"use client";

import { useReducer, useEffect, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { Settings2 } from "lucide-react";
import { API_BASE } from "../../../../constants";
import { useUIStore } from "../../../../store/useUIStore";
import { getErrorMsg } from "../../../../utils/error";
import { CONTAINER_CLASSES } from "../../../../components/ui/variants";
import LoadingSpinner from "../../../../components/ui/LoadingSpinner";
import ConfirmDialog, { useConfirm } from "../../../../components/ui/ConfirmDialog";
import type { Tag, CharacterTagLink } from "../../../../types";
import type { WizardTag } from "./steps/AppearanceStep";
import type { WizardCategory, WizardTemplate } from "./wizardTemplates";
import { WIZARD_CATEGORIES, GENDER_IDENTITY_TAGS } from "./wizardTemplates";
import { useTagData } from "../shared/useTagData";
import { wizardReducer, INITIAL_WIZARD_STATE, type WizardStep } from "./wizardReducer";
import WizardNavBar from "./components/WizardNavBar";
import WizardPreviewPanel from "./WizardPreviewPanel";
import { useWizardPreview } from "./useWizardPreview";
import GroupStep from "./steps/GroupStep";
import BasicInfoStep from "./steps/BasicInfoStep";
import AppearanceStep from "./steps/AppearanceStep";
import LoraStep from "./steps/LoraStep";
import PromptsStep from "./steps/PromptsStep";

// ── Component ────────────────────────────────────────────────

export default function CharacterWizard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();
  const [state, dispatch] = useReducer(wizardReducer, INITIAL_WIZARD_STATE);

  // Shared tag/LoRA data + search
  const {
    tagsByGroup,
    allTagsFlat,
    allLoras,
    isLoading,
    searchQuery,
    setSearchQuery,
    searchResults,
  } = useTagData();

  // ── Auto-select group from URL ?group_id=X ────────────────
  const autoGroupHandled = useRef(false);
  useEffect(() => {
    if (autoGroupHandled.current) return;
    const groupIdParam = searchParams.get("group_id");
    if (!groupIdParam) return;
    const groupId = parseInt(groupIdParam, 10);
    if (isNaN(groupId)) return;
    autoGroupHandled.current = true;

    // Fetch group data to get style_profile_id, then resolve baseModel + LoRA IDs
    axios
      .get(`${API_BASE}/groups/${groupId}`)
      .then(async (res) => {
        const g = res.data;
        const spId: number | null = g.style_profile_id ?? null;
        let baseModel: string | null = null;
        let spLoraIds: number[] = [];
        if (spId != null) {
          try {
            const spRes = await axios.get(`${API_BASE}/style-profiles/${spId}/full`);
            baseModel = spRes.data.sd_model?.base_model ?? null;
            spLoraIds = (spRes.data.loras ?? []).map((l: { id: number }) => l.id);
          } catch {
            /* fallback to null */
          }
        }
        dispatch({
          type: "SET_GROUP",
          groupId: g.id,
          styleProfileId: spId,
          baseModel,
          styleLoraIds: spLoraIds,
        });
        // Skip Step 0 by jumping to Step 1
        dispatch({ type: "SET_STEP", step: 1 });
      })
      .catch(() => {
        showToast("시리즈를 찾을 수 없습니다", "error");
      });
  }, [searchParams, showToast]);

  // ── beforeunload guard ───────────────────────────────────
  const isDirty =
    state.group_id !== null ||
    state.name.length > 0 ||
    state.description.length > 0 ||
    state.selectedTags.length > 0 ||
    state.selectedLoras.length > 0 ||
    state.positive_prompt.length > 0 ||
    state.negative_prompt.length > 0;

  useEffect(() => {
    if (!isDirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isDirty]);

  // ── Template selection ───────────────────────────────────
  const handleTemplateSelect = useCallback(
    async (template: WizardTemplate) => {
      // If already selected same template, do nothing
      if (state.templateId === template.id) return;

      // If there are existing tags, confirm replacement
      if (state.selectedTags.length > 0 && state.templateId) {
        const ok = await confirm({
          title: "Change Template",
          message: "Switching templates will replace your current tag selections. Continue?",
          confirmLabel: "Replace",
        });
        if (!ok) return;
      }

      // Resolve template tags to WizardTags using fetched data
      const resolvedTags: WizardTag[] = [];
      for (const tt of template.tags) {
        const group = tagsByGroup[tt.groupName];
        const found =
          group?.find((t) => t.name === tt.name) ?? allTagsFlat.find((t) => t.name === tt.name);
        if (found) {
          resolvedTags.push({
            tagId: found.id,
            name: found.name,
            groupName: tt.groupName,
            isPermanent: tt.isPermanent,
          });
        }
      }

      dispatch({
        type: "SELECT_TEMPLATE",
        templateId: template.id,
        tags: resolvedTags,
        gender: template.gender,
      });
    },
    [state.templateId, state.selectedTags.length, confirm, tagsByGroup, allTagsFlat]
  );

  // ── Tag toggle ───────────────────────────────────────────
  const handleToggleTag = useCallback((tag: Tag, category: WizardCategory) => {
    dispatch({
      type: "TOGGLE_TAG",
      tag: {
        tagId: tag.id,
        name: tag.name,
        groupName: category.groupName,
        isPermanent: category.isPermanent,
      },
      category,
    });
  }, []);

  const handleSearchTagSelect = useCallback(
    (tag: Tag) => {
      const category = WIZARD_CATEGORIES.find((c) => c.groupName === tag.group_name);
      if (category) {
        handleToggleTag(tag, category);
      } else {
        // Tags outside wizard categories — add as permanent identity tag
        dispatch({
          type: "ADD_TAG",
          tag: {
            tagId: tag.id,
            name: tag.name,
            groupName: tag.group_name ?? "identity",
            isPermanent: true,
          },
        });
      }
    },
    [handleToggleTag]
  );

  // ── Preview ─────────────────────────────────────────────
  const { handleGeneratePreview, assignPreview } = useWizardPreview({
    state,
    dispatch,
    allTagsFlat,
  });

  // ── Save ─────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    if (state.name.trim().length < 2) {
      showToast("Name must be at least 2 characters", "warning");
      return;
    }

    dispatch({ type: "SET_SAVING", isSaving: true });

    try {
      // Build gender identity tags
      const genderTagNames = GENDER_IDENTITY_TAGS[state.gender];
      const genderTags: CharacterTagLink[] = [];
      for (const name of genderTagNames) {
        const found = allTagsFlat.find((t) => t.name === name);
        if (found) {
          genderTags.push({ tag_id: found.id, weight: 1.0, is_permanent: true });
        }
      }

      // Build selected tags
      const selectedTagLinks: CharacterTagLink[] = state.selectedTags.map((t) => ({
        tag_id: t.tagId,
        weight: 1.0,
        is_permanent: t.isPermanent,
      }));

      // Merge (avoid duplicates)
      const seenIds = new Set<number>();
      const allTags: CharacterTagLink[] = [];
      for (const t of [...genderTags, ...selectedTagLinks]) {
        if (!seenIds.has(t.tag_id)) {
          seenIds.add(t.tag_id);
          allTags.push(t);
        }
      }

      const payload = {
        name: state.name.trim(),
        gender: state.gender,
        description: state.description.trim() || null,
        group_id: state.group_id,
        tags: allTags,
        loras: state.selectedLoras.map((l) => ({ lora_id: l.loraId, weight: l.weight })),
        positive_prompt: state.positive_prompt.trim() || null,
        negative_prompt: state.negative_prompt.trim() || null,
      };

      const res = await axios.post(`${API_BASE}/characters`, payload);
      await assignPreview(res.data.id);
      showToast("Character created!", "success");
      router.push(`/library/characters/${res.data.id}`);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        showToast("A character with this name already exists", "error");
      } else {
        showToast(getErrorMsg(err, "Failed to create character"), "error");
      }
    } finally {
      dispatch({ type: "SET_SAVING", isSaving: false });
    }
  }, [state, allTagsFlat, showToast, router, assignPreview]);

  // ── Navigation ───────────────────────────────────────────
  const requiredCategories = WIZARD_CATEGORIES.filter((c) => c.isRequired);
  const allRequiredSelected = requiredCategories.every((cat) =>
    state.selectedTags.some((t) => t.groupName === cat.groupName)
  );

  const canProceed =
    state.step === 0
      ? state.group_id !== null
      : state.step === 1
        ? state.name.trim().length >= 2
        : state.step === 2
          ? allRequiredSelected
          : true;

  const handleNext = useCallback(async () => {
    if (state.step < 4) {
      dispatch({ type: "SET_STEP", step: (state.step + 1) as WizardStep });
      return;
    }
    await handleSave();
  }, [state.step, handleSave]);

  const handleBack = useCallback(() => {
    if (state.step > 0) {
      dispatch({ type: "SET_STEP", step: (state.step - 1) as WizardStep });
    }
  }, [state.step]);

  // ── Step headers ─────────────────────────────────────────
  const stepLabels = ["Series", "Basic Info", "Appearance", "LoRA", "Prompts"];

  // ── Loading ──────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className={`${CONTAINER_CLASSES} flex items-center justify-center py-32`}>
        <LoadingSpinner size="md" />
      </div>
    );
  }

  return (
    <div className={`${CONTAINER_CLASSES} py-6`}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-lg font-bold text-zinc-900">Character Builder</h1>
        <Link
          href="/library/characters/new?mode=full"
          className="flex items-center gap-1 text-xs font-medium text-zinc-400 hover:text-zinc-600"
        >
          <Settings2 className="h-3.5 w-3.5" />
          Full Editor
        </Link>
      </div>

      {/* Step tabs */}
      <div className="mb-4 flex items-center gap-4 border-b border-zinc-100 pb-2">
        {stepLabels.map((label, i) => (
          <button
            key={label}
            onClick={() => {
              const target = i as WizardStep;
              if (target < state.step || (target > state.step && canProceed)) {
                dispatch({ type: "SET_STEP", step: target });
              }
            }}
            className={`text-sm font-medium transition ${
              state.step === i
                ? "border-b-2 border-zinc-900 pb-1 text-zinc-900"
                : "pb-1 text-zinc-400 hover:text-zinc-600"
            }`}
          >
            {i + 1}. {label}
          </button>
        ))}
      </div>

      {/* Two-column layout */}
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Left: Preview panel */}
        <WizardPreviewPanel
          name={state.name}
          gender={state.gender}
          selectedTags={state.selectedTags}
          selectedLoras={state.selectedLoras}
          allLoras={allLoras}
          previewImage={state.previewImage}
          isGenerating={state.isGenerating}
          candidates={state.previewCandidates}
          selectedCandidateIndex={state.selectedCandidateIndex}
          onGeneratePreview={handleGeneratePreview}
          onSelectCandidate={(index) => dispatch({ type: "SELECT_CANDIDATE", index })}
        />

        {/* Right: Step content */}
        <div className="rounded-2xl border border-zinc-200/60 bg-white p-5">
          {state.step === 0 && (
            <GroupStep
              selectedGroupId={state.group_id}
              onSelect={(groupId, styleProfileId, baseModel, styleLoraIds) =>
                dispatch({ type: "SET_GROUP", groupId, styleProfileId, baseModel, styleLoraIds })
              }
            />
          )}
          {state.step === 1 && (
            <BasicInfoStep
              name={state.name}
              gender={state.gender}
              description={state.description}
              templateId={state.templateId}
              onNameChange={(v) => dispatch({ type: "SET_NAME", name: v })}
              onGenderChange={(v) => dispatch({ type: "SET_GENDER", gender: v })}
              onDescriptionChange={(v) => dispatch({ type: "SET_DESCRIPTION", description: v })}
              onTemplateSelect={handleTemplateSelect}
            />
          )}
          {state.step === 2 && (
            <AppearanceStep
              tagsByGroup={tagsByGroup}
              selectedTags={state.selectedTags}
              onToggleTag={handleToggleTag}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              searchResults={searchResults}
              onSearchTagSelect={handleSearchTagSelect}
            />
          )}
          {state.step === 3 && (
            <LoraStep
              allLoras={allLoras}
              selectedLoras={state.selectedLoras}
              gender={state.gender}
              styleBaseModel={state.styleBaseModel}
              excludeLoraIds={state.styleLoraIds}
              onToggleLora={(loraId, defaultWeight) =>
                dispatch({ type: "TOGGLE_LORA", loraId, defaultWeight })
              }
              onUpdateWeight={(loraId, weight) =>
                dispatch({ type: "UPDATE_LORA_WEIGHT", loraId, weight })
              }
            />
          )}
          {state.step === 4 && (
            <PromptsStep
              positivePrompt={state.positive_prompt}
              negativePrompt={state.negative_prompt}
              selectedTagNames={state.selectedTags.map((t) => t.name)}
              onFieldChange={(field, value) => dispatch({ type: "SET_PROMPT_FIELD", field, value })}
            />
          )}
        </div>
      </div>

      {/* Bottom nav */}
      <WizardNavBar
        step={state.step}
        totalSteps={5}
        onBack={handleBack}
        onNext={handleNext}
        isSaving={state.isSaving}
        isLastStep={state.step === 4}
        canProceed={canProceed}
        onSkipToEnd={handleSave}
      />

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
