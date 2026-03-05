import type { Scene } from "../../types";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { generateSceneClientId } from "../../utils/uuid";
import type { SceneItem } from "./types";

/**
 * Shared Scene → SceneItem mapper. preserveClientId keeps existing client_id from loaded data.
 * Spread passthrough: Scene 필드를 그대로 전달하고 필수 기본값만 오버라이드.
 */
function mapScenesToItems(scenes: Scene[], opts?: { preserveClientId?: boolean }): SceneItem[] {
  return scenes.map((s, i) => ({
    ...(s as unknown as SceneItem),
    // Required field overrides
    id: s.id ?? i + 1,
    client_id: opts?.preserveClientId
      ? (s.client_id ?? generateSceneClientId())
      : generateSceneClientId(),
    order: s.order ?? i + 1,
    script: s.script ?? "",
    speaker: s.speaker ?? "Narrator",
    duration: s.duration ?? 3,
    image_prompt: s.image_prompt ?? "",
    image_prompt_ko: s.image_prompt_ko ?? "",
    image_url: s.image_url ?? null,
  }));
}

/** Map SSE event scenes → SceneItem[] (always generates new client_id). */
export function mapEventScenes(scenes: Scene[]): SceneItem[] {
  return mapScenesToItems(scenes);
}

/** Map storyboard API response scenes → SceneItem[] (preserves existing client_id). */
export function mapLoadedScenes(scenes: Scene[]): SceneItem[] {
  return mapScenesToItems(scenes, { preserveClientId: true });
}

export type SyncMeta = {
  topic: string;
  description: string;
  duration: number;
  language: string;
  structure: string;
  characterId?: number | null;
  characterName?: string | null;
  characterBId?: number | null;
  characterBName?: string | null;
};

/**
 * Map local SceneItem[] → global Scene[] and sync to useStoryboardStore.
 * Spread passthrough: SceneItem 필드를 그대로 전달하고 Scene 전용 필드만 추가/오버라이드.
 */
export function syncToGlobalStore(scenes: SceneItem[], meta: SyncMeta) {
  const mapped = scenes.map((s, i) => ({
    ...(s as unknown as Scene),
    // Required overrides
    id: s.id ?? i + 1,
    order: s.order ?? i + 1,
    speaker: s.speaker as Scene["speaker"],
    negative_prompt: s.negative_prompt_extra || "",
    // UI-only fields (always reset)
    isGenerating: false,
    debug_payload: "",
  }));
  useStoryboardStore.getState().setScenes(mapped);
  const { characterId, characterName, characterBId, characterBName, ...rest } = meta;
  useStoryboardStore.getState().set({
    ...rest,
    selectedCharacterId: characterId ?? null,
    selectedCharacterName: characterName ?? null,
    selectedCharacterBId: characterBId ?? null,
    selectedCharacterBName: characterBName ?? null,
  });
}
