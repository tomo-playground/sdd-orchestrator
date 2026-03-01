import type React from "react";
import { syncToGlobalStore } from "./mappers";
import type { SceneItem, ScriptEditorState } from "./types";
import type { SyncMeta } from "./mappers";

/** Build SyncMeta from ScriptEditorState. */
export function buildSyncMeta(s: ScriptEditorState): SyncMeta {
  return {
    topic: s.topic.trim(),
    description: s.description.trim(),
    duration: s.duration,
    language: s.language,
    structure: s.structure,
    characterId: s.characterId,
    characterName: s.characterName,
    characterBId: s.characterBId,
    characterBName: s.characterBName,
  };
}

/** Build POST body for /scripts/generate-stream. */
export function buildGenerateBody(
  s: ScriptEditorState,
  groupId: number | null
): Record<string, unknown> {
  const body: Record<string, unknown> = {
    topic: s.topic.trim(),
    description: s.description.trim() || undefined,
    duration: s.duration,
    language: s.language,
    structure: s.structure,
    group_id: groupId,
    interaction_mode: s.interactionMode,
  };
  if (s.characterId) body.character_id = s.characterId;
  if (s.characterBId) body.character_b_id = s.characterBId;
  const refs = s.references.trim();
  if (refs) {
    body.references = refs
      .split("\n")
      .map((r) => r.trim())
      .filter(Boolean);
  }
  return body;
}

/** Build PUT/POST body for /storyboards. */
export function buildSavePayload(s: ScriptEditorState, groupId: number | null) {
  return {
    title: s.topic.trim(),
    description: s.description.trim() || undefined,
    duration: s.duration,
    language: s.language,
    structure: s.structure,
    group_id: groupId,
    character_id: s.characterId,
    character_b_id: s.characterBId,
    version: s.storyboardVersion ?? undefined,
    scenes: s.scenes.map((sc, i) => ({
      scene_id: i,
      client_id: sc.client_id,
      script: sc.script,
      speaker: sc.speaker,
      duration: sc.duration,
      image_prompt: sc.image_prompt,
      image_prompt_ko: sc.image_prompt_ko,
      use_controlnet: sc.use_controlnet ?? null,
      controlnet_weight: sc.controlnet_weight ?? null,
      controlnet_pose: sc.controlnet_pose ?? null,
      use_ip_adapter: sc.use_ip_adapter ?? null,
      ip_adapter_weight: sc.ip_adapter_weight ?? null,
      multi_gen_enabled: sc.multi_gen_enabled ?? null,
      voice_design_prompt: sc.voice_design_prompt ?? null,
      head_padding: sc.head_padding ?? null,
      tail_padding: sc.tail_padding ?? null,
      background_id: sc.background_id ?? null,
      ken_burns_preset: sc.ken_burns_preset ?? null,
      context_tags: sc.context_tags ?? null,
    })),
  };
}

type StreamOutcomeOpts = {
  finalScenes: SceneItem[] | null;
  isWaiting: boolean;
  meta: SyncMeta;
  setState: React.Dispatch<React.SetStateAction<ScriptEditorState>>;
  dirtyRef: React.MutableRefObject<boolean>;
  showToast: (msg: string, type: "success" | "error" | "warning") => void;
};

/** Shared post-stream handler for generate & resume. Returns true if scenes were produced. */
export function handleStreamOutcome(opts: StreamOutcomeOpts): boolean {
  const { finalScenes, isWaiting, meta, setState, dirtyRef, showToast } = opts;
  if (isWaiting) return false;
  if (finalScenes) {
    setState((prev) => ({
      ...prev,
      scenes: finalScenes,
      isGenerating: false,
      progress: null,
      isWaitingForInput: false,
      justGenerated: true,
    }));
    syncToGlobalStore(finalScenes, meta);
    dirtyRef.current = false;
    showToast("Script generated", "success");
    return true;
  }
  setState((prev) => ({ ...prev, isGenerating: false, progress: null }));
  showToast("No scenes returned", "warning");
  return false;
}
