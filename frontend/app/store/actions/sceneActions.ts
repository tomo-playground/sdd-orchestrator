import axios from "axios";
import type { Scene, FixSuggestion } from "../../types";
import { useStudioStore } from "../useStudioStore";
import { API_BASE, CAMERA_KEYWORDS, ACTION_KEYWORDS, BACKGROUND_KEYWORDS } from "../../constants";
import { computeValidationResults, getFixSuggestions } from "../../utils";
import { buildNegativePrompt } from "./promptActions";
import { resolveCharacterIdForSpeaker } from "../../utils/speakerResolver";

// --------------- Validation ---------------

export function runValidation() {
  const { scenes } = useStudioStore.getState();
  const { results, summary } = computeValidationResults(scenes);
  useStudioStore.getState().setScenesState({
    validationResults: results,
    validationSummary: summary,
  });
}

export function applyAutoFixForScenes(inputScenes: Scene[]): Scene[] {
  const { topic, baseNegativePromptA } = useStudioStore.getState();
  const { results, summary } = computeValidationResults(inputScenes);
  useStudioStore.getState().setScenesState({
    validationResults: results,
    validationSummary: summary,
  });

  let updated = [...inputScenes];
  updated.forEach((scene) => {
    const validation = results[scene.id];
    if (!validation || validation.status === "ok") return;
    const suggestions = getFixSuggestions(scene, validation, topic);
    suggestions
      .filter((s) => s.action)
      .forEach((s) => {
        if (!s.action) return;
        if (s.action.type === "set_speaker_a") {
          updated = updated.map((t) =>
            t.id === scene.id
              ? {
                  ...t,
                  speaker: "A" as const,
                  negative_prompt: baseNegativePromptA,
                }
              : t
          );
        } else if (s.action.type === "add_positive") {
          const tokens = s.action.tokens ?? [];
          if (!tokens.length) return;
          updated = updated.map((t) => {
            if (t.id !== scene.id) return t;
            const existing = t.image_prompt
              .split(",")
              .map((x) => x.trim())
              .filter(Boolean);
            const existingSet = new Set(existing.map((x) => x.toLowerCase()));
            const next = [...existing];
            tokens.forEach((tok) => {
              if (!existingSet.has(tok.toLowerCase())) next.push(tok);
            });
            return { ...t, image_prompt: next.join(", ") };
          });
        } else if (s.action.type === "fill_script" || s.action.type === "trim_script") {
          const value = s.action.value?.trim() || "";
          if (!value) return;
          updated = updated.map((t) => (t.id === scene.id ? { ...t, script: value } : t));
        } else if (s.action.type === "remove_negative_scene") {
          const kws = [...CAMERA_KEYWORDS, ...ACTION_KEYWORDS, ...BACKGROUND_KEYWORDS];
          updated = updated.map((t) => {
            if (t.id !== scene.id) return t;
            const filtered = t.negative_prompt
              .split(",")
              .map((x) => x.trim())
              .filter(Boolean)
              .filter((tok) => !kws.some((kw) => tok.toLowerCase().includes(kw)));
            return { ...t, negative_prompt: filtered.join(", ") };
          });
        }
      });
  });
  return updated;
}

export function handleAutoFixAll() {
  const { scenes, setScenes } = useStudioStore.getState();
  const updated = applyAutoFixForScenes(scenes);
  setScenes(updated);
  setTimeout(() => runValidation(), 0);
}

// --------------- Scene Status ---------------

export function getSceneStatus(scene: Scene): string {
  const { imageValidationResults } = useStudioStore.getState();
  if (!scene.image_url) return "Need Image";
  if (!imageValidationResults[scene.id]) return "Ready to Validate";
  return "Ready to Render";
}

export function getSceneFixSuggestions(scene: Scene): FixSuggestion[] {
  const { validationResults, topic } = useStudioStore.getState();
  const validation = validationResults[scene.id];
  if (!validation) return [];
  return getFixSuggestions(scene, validation, topic);
}

// --------------- Apply Suggestion ---------------

export function applySuggestion(scene: Scene, suggestion: FixSuggestion) {
  const { updateScene } = useStudioStore.getState();
  if (!suggestion.action) return;

  if (suggestion.action.type === "set_speaker_a") {
    handleSpeakerChange(scene, "A");
    return;
  }

  const splitTokens = (text: string) =>
    text
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

  if (suggestion.action.type === "add_positive") {
    const tokens = suggestion.action.tokens ?? [];
    if (!tokens.length) return;
    const existing = splitTokens(scene.image_prompt);
    const existingSet = new Set(existing.map((t) => t.toLowerCase()));
    const next = [...existing];
    if (suggestion.id === "missing-background") {
      const candidate = tokens.find((t) => !existingSet.has(t.toLowerCase()));
      if (candidate) next.push(candidate);
    } else {
      tokens.forEach((t) => {
        if (!existingSet.has(t.toLowerCase())) next.push(t);
      });
    }
    updateScene(scene.id, { image_prompt: next.join(", ") });
    return;
  }

  if (suggestion.action.type === "remove_negative_scene") {
    const kws = [...CAMERA_KEYWORDS, ...ACTION_KEYWORDS, ...BACKGROUND_KEYWORDS];
    const filtered = splitTokens(scene.negative_prompt).filter(
      (tok) => !kws.some((kw) => tok.toLowerCase().includes(kw))
    );
    updateScene(scene.id, { negative_prompt: filtered.join(", ") });
  }
}

// --------------- Apply Missing Tags ---------------

export function applyMissingImageTags(scene: Scene, missingOverride?: string[], limit = 5) {
  const { imageValidationResults, updateScene, showToast } = useStudioStore.getState();
  const missing = missingOverride ?? imageValidationResults[scene.id]?.missing ?? [];
  if (!missing.length) {
    showToast("No missing tags to add", "error");
    return;
  }
  const existing = scene.image_prompt
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
  const existingSet = new Set(existing.map((t) => t.toLowerCase()));
  const next = [...existing];
  let addedCount = 0;
  missing.slice(0, limit).forEach((tok) => {
    if (!existingSet.has(tok.toLowerCase())) {
      next.push(tok);
      addedCount++;
    }
  });
  if (addedCount > 0) {
    updateScene(scene.id, { image_prompt: next.join(", ") });
    showToast(`Added ${addedCount} tags to prompt`, "success");
  } else {
    showToast("All tags already in prompt", "error");
  }
}

// --------------- Speaker Change ---------------

export function handleSpeakerChange(scene: Scene, speaker: Scene["speaker"]) {
  const { baseNegativePromptA, baseNegativePromptB, updateScene } = useStudioStore.getState();
  updateScene(scene.id, {
    speaker,
    negative_prompt: speaker === "B" ? baseNegativePromptB : baseNegativePromptA,
  });
}

// --------------- Image Validation ---------------

export async function handleValidateImage(scene: Scene) {
  const { showToast } = useStudioStore.getState();
  if (!scene.image_url) {
    showToast("Upload or generate an image first.", "error");
    return;
  }
  useStudioStore.getState().setScenesState({ validatingSceneId: scene.id });
  const prompt = scene.debug_prompt || scene.image_prompt;
  const { storyboardId } = useStudioStore.getState();

  try {
    const res = await axios.post(`${API_BASE}/scene/validate-and-auto-edit`, {
      image_b64: scene.image_url,
      prompt,
      storyboard_id: storyboardId,
      scene_id: scene.id,
    });
    const prev = useStudioStore.getState().imageValidationResults;
    useStudioStore.getState().setScenesState({
      imageValidationResults: { ...prev, [scene.id]: res.data },
    });
    const matchRate = Math.round((res.data.match_rate || 0) * 100);

    if (scene.prompt_history_id && res.data.match_rate != null) {
      axios
        .post(
          `${API_BASE}/prompt-histories/${scene.prompt_history_id}/update-score?match_rate=${matchRate}`
        )
        .catch(() => {});
    }
    if (matchRate >= 80) {
      showToast(`Validated! Match ${matchRate}%`, "success");
    } else {
      showToast(`Match ${matchRate}% - check missing tags`, "error");
    }
  } catch {
    showToast("Image validation failed", "error");
  } finally {
    useStudioStore.getState().setScenesState({ validatingSceneId: null });
  }
}

// --------------- Mark Success / Fail ---------------

export async function handleMarkSuccess(scene: Scene) {
  const { showToast } = useStudioStore.getState();
  if (!scene.activity_log_id) {
    showToast("No generation log to mark", "error");
    return;
  }
  useStudioStore.getState().setScenesState({
    markingStatusSceneId: scene.id,
  });
  try {
    await axios.patch(`${API_BASE}/activity-logs/${scene.activity_log_id}/status`, {
      status: "success",
    });
    showToast("Marked as success", "success");
  } catch {
    showToast("Failed to mark status", "error");
  } finally {
    useStudioStore.getState().setScenesState({ markingStatusSceneId: null });
  }
}

export async function handleMarkFail(scene: Scene) {
  const { showToast } = useStudioStore.getState();
  if (!scene.activity_log_id) {
    showToast("No generation log to mark", "error");
    return;
  }
  useStudioStore.getState().setScenesState({
    markingStatusSceneId: scene.id,
  });
  try {
    await axios.patch(`${API_BASE}/activity-logs/${scene.activity_log_id}/status`, {
      status: "fail",
    });
    showToast("Marked as fail", "error");
  } catch {
    showToast("Failed to mark status", "error");
  } finally {
    useStudioStore.getState().setScenesState({ markingStatusSceneId: null });
  }
}

// --------------- Save Prompt ---------------

export async function handleSavePrompt(scene: Scene) {
  const state = useStudioStore.getState();
  const { characterLoras, showToast } = state;
  const characterId = resolveCharacterIdForSpeaker(scene.speaker, state);
  const name = window.prompt("Enter a name for this prompt:");
  if (!name?.trim()) return;

  try {
    const payload: Record<string, unknown> = {
      name: name.trim(),
      positive_prompt: scene.debug_prompt || scene.image_prompt,
      negative_prompt: buildNegativePrompt(scene),
      context_tags: scene.context_tags ? Object.values(scene.context_tags).flat() : [],
    };
    if (characterId) payload.character_id = characterId;
    if (characterLoras?.length) {
      payload.lora_settings = characterLoras.map((lora) => ({
        lora_id: lora.id ?? 0,
        name: lora.name,
        weight: lora.optimal_weight ?? lora.weight ?? 0.7,
        trigger_words: lora.trigger_words ?? [],
      }));
    }
    await axios.post(`${API_BASE}/prompt-histories`, payload);
    showToast("Prompt saved!", "success");
  } catch {
    showToast("Failed to save prompt", "error");
  }
}
