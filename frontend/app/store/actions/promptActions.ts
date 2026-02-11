import axios from "axios";
import type { Scene } from "../../types";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import { splitPromptTokens, deduplicatePromptTokens } from "../../utils";
import { API_BASE } from "../../constants";
import {
  resolveCharacterIdForSpeaker,
  resolveNegativePromptForSpeaker,
} from "../../utils/speakerResolver";

export function buildNegativePrompt(scene: Scene): string {
  const { autoComposePrompt, baseNegativePromptA, baseNegativePromptB } =
    useStoryboardStore.getState();
  const base = resolveNegativePromptForSpeaker(
    scene.speaker,
    baseNegativePromptA,
    baseNegativePromptB
  ).trim();
  const sceneNeg = scene.negative_prompt.trim();
  if (!autoComposePrompt) return sceneNeg;
  const combined = base && sceneNeg ? `${base}, ${sceneNeg}` : base || sceneNeg;
  return deduplicatePromptTokens(combined);
}

export async function buildScenePrompt(scene: Scene): Promise<string | null> {
  const sbState = useStoryboardStore.getState();
  const ctxState = useContextStore.getState();
  const { autoComposePrompt } = sbState;
  const characterId = resolveCharacterIdForSpeaker(scene.speaker, sbState);

  const scenePrompt = scene.image_prompt.trim();
  if (!autoComposePrompt) return scenePrompt || null;
  if (!characterId) return scenePrompt || null;

  const sceneTokens = scenePrompt ? splitPromptTokens(scenePrompt) : [];
  if (sceneTokens.length === 0) return null;

  try {
    // Style LoRAs resolved by Backend from storyboard -> group -> style_profile (SSOT)
    const res = await axios.post(`${API_BASE}/prompt/compose`, {
      tokens: sceneTokens,
      character_id: characterId,
      character_b_id: sbState.selectedCharacterBId || undefined,
      storyboard_id: ctxState.storyboardId || undefined,
      scene_id: scene.id > 0 ? scene.id : undefined,
      context_tags: scene.context_tags || undefined,
      use_break: false,
    });
    if (res.data.prompt) return res.data.prompt;
  } catch {
    // fallback: join tokens
  }

  return sceneTokens.join(", ");
}
