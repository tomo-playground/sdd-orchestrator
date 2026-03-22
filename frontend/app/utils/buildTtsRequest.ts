/**
 * Build a TTS request payload from scene + storyboard context.
 * SSOT: all TTS calls (preview, prebuild, autopilot) use this function.
 * Mirrors the image generation pattern of buildSceneRequest().
 */
import type { Scene } from "@/app/types";

export interface TtsScenePayload {
  scene_db_id: number | null;
  script: string;
  speaker: string;
  voice_design_prompt: string | null;
  scene_emotion: string | undefined;
  image_prompt_ko: string | undefined;
  language: string;
  storyboard_id: number | null;
}

export function buildTtsRequest(
  scene: Scene,
  language: string,
  storyboardId: number | null
): TtsScenePayload {
  return {
    scene_db_id: scene.id ?? null,
    script: scene.script || "",
    speaker: scene.speaker || "Narrator", // TODO: sync with backend DEFAULT_SPEAKER
    voice_design_prompt: scene.voice_design_prompt || null,
    scene_emotion: Array.isArray(scene.context_tags?.emotion)
      ? scene.context_tags.emotion.join(", ")
      : (scene.context_tags?.emotion ?? undefined),
    image_prompt_ko: scene.image_prompt_ko ?? undefined,
    language,
    storyboard_id: storyboardId,
  };
}
