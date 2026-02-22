import type { Scene } from "../../types";
import { useStoryboardStore } from "../useStoryboardStore";
import { deduplicatePromptTokens } from "../../utils";
import { resolveNegativePromptForSpeaker } from "../../utils/speakerResolver";

export function buildNegativePrompt(scene: Scene): string {
  const { baseNegativePromptA, baseNegativePromptB } =
    useStoryboardStore.getState();
  const base = resolveNegativePromptForSpeaker(
    scene.speaker,
    baseNegativePromptA,
    baseNegativePromptB
  ).trim();
  const sceneNeg = scene.negative_prompt.trim();
  const combined = base && sceneNeg ? `${base}, ${sceneNeg}` : base || sceneNeg;
  return deduplicatePromptTokens(combined);
}

/** Return raw image_prompt — Backend handles V3 composition via context_tags. */
export function buildScenePrompt(scene: Scene): string | null {
  return scene.image_prompt.trim() || null;
}
