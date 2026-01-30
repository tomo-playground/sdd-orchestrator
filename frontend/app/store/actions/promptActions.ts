import axios from "axios";
import type { Scene } from "../../types";
import { useStudioStore } from "../useStudioStore";
import {
  splitPromptTokens,
  mergePromptTokens,
  deduplicatePromptTokens,
  getGenderEnhancements,
  fixCameraPoseConflicts,
} from "../../utils";
import {
  API_BASE,
  SCENE_SPECIFIC_KEYWORDS,
  getTokenPriority,
} from "../../constants";

export function getBasePromptForScene(_scene: Scene): string {
  const { basePromptA } = useStudioStore.getState();
  return basePromptA.trim();
}

export function getBaseSettingsForSpeaker(_speaker: Scene["speaker"]) {
  const { baseStepsA, baseCfgScaleA, baseSamplerA, baseSeedA, baseClipSkipA } =
    useStudioStore.getState();
  return {
    steps: baseStepsA,
    cfg: baseCfgScaleA,
    sampler: baseSamplerA,
    seed: baseSeedA,
    clipSkip: baseClipSkipA,
  };
}

/** Collect context tags into a flat array */
function collectContextTags(scene: Scene): string[] {
  const list: string[] = [];
  if (!scene.context_tags) return list;
  const { expression, gaze, pose, action, camera, environment, mood } =
    scene.context_tags;
  if (expression?.length) list.push(...expression);
  if (gaze) list.push(gaze);
  if (pose?.length) list.push(...pose);
  if (action?.length) list.push(...action);
  if (camera) list.push(camera);
  if (environment?.length) list.push(...environment);
  if (mood?.length) list.push(...mood);
  return list;
}

export function buildPositivePrompt(scene: Scene): string {
  const { autoComposePrompt } = useStudioStore.getState();
  const base = getBasePromptForScene(scene);
  const scenePrompt = scene.image_prompt.trim();
  const contextTagsList = collectContextTags(scene);

  const baseTokens = base ? splitPromptTokens(base) : [];
  const sceneTokens = scenePrompt ? splitPromptTokens(scenePrompt) : [];

  const filteredBaseTokens = autoComposePrompt
    ? baseTokens.filter((token) => {
        const lower = token.toLowerCase();
        return !SCENE_SPECIFIC_KEYWORDS.some((kw) => lower.includes(kw));
      })
    : baseTokens;

  const allTokens = mergePromptTokens(filteredBaseTokens, [
    ...contextTagsList,
    ...sceneTokens,
  ]);
  const fixedTokens = fixCameraPoseConflicts(allTokens);
  const sortedTokens = [...fixedTokens].sort(
    (a, b) => getTokenPriority(a) - getTokenPriority(b)
  );
  return sortedTokens.join(", ");
}

export function buildNegativePrompt(scene: Scene): string {
  const { autoComposePrompt, baseNegativePromptA } =
    useStudioStore.getState();
  const base = baseNegativePromptA.trim();
  const sceneNeg = scene.negative_prompt.trim();
  if (!autoComposePrompt) return sceneNeg;
  const combined =
    base && sceneNeg ? `${base}, ${sceneNeg}` : base || sceneNeg;
  return deduplicatePromptTokens(combined);
}

export async function buildScenePrompt(
  scene: Scene
): Promise<string | null> {
  const { autoComposePrompt, characterPromptMode, characterLoras } =
    useStudioStore.getState();
  const basePrompt = getBasePromptForScene(scene);
  const scenePrompt = scene.image_prompt.trim();

  if (!autoComposePrompt) return scenePrompt || null;

  const baseTokens = basePrompt ? splitPromptTokens(basePrompt) : [];
  const sceneTokens = scenePrompt ? splitPromptTokens(scenePrompt) : [];
  const contextTagsList = collectContextTags(scene);

  const allTokens = mergePromptTokens(baseTokens, [
    ...contextTagsList,
    ...sceneTokens,
  ]);
  if (allTokens.length === 0) return null;

  // Gender enhancements
  const genderEnhancements = getGenderEnhancements(baseTokens);
  if (genderEnhancements.positive.length > 0) {
    allTokens.push(...genderEnhancements.positive);
  }

  let fixedTokens = fixCameraPoseConflicts(allTokens);

  // DB-based conflict check
  try {
    const res = await axios.post(`${API_BASE}/prompt/check-conflicts`, {
      tags: fixedTokens,
    });
    if (res.data.has_conflicts) {
      fixedTokens = res.data.filtered_tags;
    }
  } catch {
    // continue on failure
  }

  // Compose via backend API
  try {
    const composeRes = await axios.post(`${API_BASE}/prompt/compose`, {
      tokens: fixedTokens,
      mode: characterPromptMode,
      loras:
        characterLoras.length > 0
          ? characterLoras.map((lora) => ({
              name: lora.name,
              weight: lora.weight ?? 0.5,
              trigger_words: lora.trigger_words ?? [],
              lora_type: lora.lora_type ?? "character",
              optimal_weight: lora.optimal_weight,
            }))
          : [],
      use_break: true,
    });
    if (composeRes.data.prompt) return composeRes.data.prompt;
  } catch {
    // fallback below
  }

  return fixedTokens.join(", ");
}
