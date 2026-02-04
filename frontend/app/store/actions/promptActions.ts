import axios from "axios";
import type { Scene } from "../../types";
import { useStudioStore } from "../useStudioStore";
import { splitPromptTokens, deduplicatePromptTokens } from "../../utils";
import { API_BASE } from "../../constants";

export function buildNegativePrompt(scene: Scene): string {
  const { autoComposePrompt, baseNegativePromptA } = useStudioStore.getState();
  const base = baseNegativePromptA.trim();
  const sceneNeg = scene.negative_prompt.trim();
  if (!autoComposePrompt) return sceneNeg;
  const combined = base && sceneNeg ? `${base}, ${sceneNeg}` : base || sceneNeg;
  return deduplicatePromptTokens(combined);
}

export async function buildScenePrompt(scene: Scene): Promise<string | null> {
  const { autoComposePrompt, selectedCharacterId } = useStudioStore.getState();

  const scenePrompt = scene.image_prompt.trim();
  if (!autoComposePrompt) return scenePrompt || null;
  if (!selectedCharacterId) return scenePrompt || null;

  const sceneTokens = scenePrompt ? splitPromptTokens(scenePrompt) : [];
  if (sceneTokens.length === 0) return null;

  try {
    // base_prompt / loras are NOT sent — Backend loads from DB via character_id (SSOT)
    const res = await axios.post(`${API_BASE}/prompt/compose`, {
      tokens: sceneTokens,
      character_id: selectedCharacterId,
      context_tags: scene.context_tags || undefined,
      use_break: false,
    });
    if (res.data.prompt) return res.data.prompt;
  } catch {
    // fallback: join tokens
  }

  return sceneTokens.join(", ");
}
