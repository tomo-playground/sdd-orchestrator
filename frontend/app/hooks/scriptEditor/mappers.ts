import type { Scene } from "../../types";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { generateSceneClientId } from "../../utils/uuid";
import type { SceneItem } from "./types";

/** Shared Scene → SceneItem mapper. preserveClientId keeps existing client_id from loaded data. */
function mapScenesToItems(scenes: Scene[], opts?: { preserveClientId?: boolean }): SceneItem[] {
  return scenes.map((s, i) => ({
    id: s.id ?? i + 1,
    client_id: opts?.preserveClientId ? (s.client_id ?? generateSceneClientId()) : generateSceneClientId(),
    order: s.order ?? i + 1,
    script: s.script ?? "",
    speaker: s.speaker ?? "Narrator",
    duration: s.duration ?? 3,
    image_prompt: s.image_prompt ?? "",
    image_prompt_ko: s.image_prompt_ko ?? "",
    image_url: s.image_url ?? null,
    context_tags: s.context_tags ?? undefined,
    character_actions: s.character_actions ?? undefined,
    use_controlnet: s.use_controlnet ?? undefined,
    controlnet_weight: s.controlnet_weight ?? undefined,
    controlnet_pose: s.controlnet_pose ?? undefined,
    use_ip_adapter: s.use_ip_adapter ?? undefined,
    ip_adapter_weight: s.ip_adapter_weight ?? undefined,
    multi_gen_enabled: s.multi_gen_enabled ?? undefined,
    negative_prompt_extra: s.negative_prompt_extra ?? undefined,
    voice_design_prompt: s.voice_design_prompt ?? undefined,
    head_padding: s.head_padding ?? undefined,
    tail_padding: s.tail_padding ?? undefined,
    ken_burns_preset: s.ken_burns_preset ?? undefined,
    background_id: s.background_id ?? null,
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

/** Map local SceneItem[] → global Scene[] and sync to useStoryboardStore. */
export function syncToGlobalStore(scenes: SceneItem[], meta: SyncMeta) {
  const mapped = scenes.map((s, i) => ({
    id: s.id ?? i + 1,
    client_id: s.client_id,
    order: s.order ?? i + 1,
    script: s.script,
    speaker: s.speaker as Scene["speaker"],
    duration: s.duration,
    image_prompt: s.image_prompt,
    image_prompt_ko: s.image_prompt_ko,
    image_url: s.image_url,
    negative_prompt: "",
    isGenerating: false,
    debug_payload: "",
    context_tags: s.context_tags,
    character_actions: s.character_actions,
    use_controlnet: s.use_controlnet,
    controlnet_weight: s.controlnet_weight,
    controlnet_pose: s.controlnet_pose,
    use_ip_adapter: s.use_ip_adapter,
    ip_adapter_weight: s.ip_adapter_weight,
    multi_gen_enabled: s.multi_gen_enabled,
    negative_prompt_extra: s.negative_prompt_extra,
    voice_design_prompt: s.voice_design_prompt,
    head_padding: s.head_padding,
    tail_padding: s.tail_padding,
    ken_burns_preset: s.ken_burns_preset,
    background_id: s.background_id ?? null,
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
