import type React from "react";
import { useStoryboardStore } from "../../store/useStoryboardStore";
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
    group_id: groupId,
    interaction_mode: s.interactionMode,
    // structure, character_id, character_b_id는 전달하지 않음
    // → Director가 주제 분석 후 캐스팅(구조+캐릭터) 결정 → plan_review에서 사용자 승인/수정
  };
  const refs = s.references.trim();
  if (refs) {
    body.references = refs
      .split("\n")
      .map((r) => r.trim())
      .filter(Boolean);
  }
  if (s.chatContext?.length) {
    body.chat_context = s.chatContext;
  }
  return body;
}

/** Build PUT/POST body for /storyboards. */
export function buildSavePayload(s: ScriptEditorState, groupId: number | null) {
  const casting = useStoryboardStore.getState().castingRecommendation;
  return {
    title: s.topic.trim(),
    description: s.description.trim() || undefined,
    duration: s.duration,
    language: s.language,
    structure: s.structure,
    group_id: groupId,
    character_id: s.characterId,
    character_b_id: s.characterBId,
    casting_recommendation: casting ?? undefined,
    version: s.storyboardVersion ?? undefined,
    // Spread passthrough: UI-only 필드 제거 후 나머지 패스스루
    scenes: s.scenes.map((sc, i) => {
      const {
        id: _id,
        order: _order,
        image_url: _imageUrl,
        negative_prompt_extra: _extra,
        ...rest
      } = sc;
      return { ...rest, scene_id: i };
    }),
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
    // Director 캐스팅 결과를 editor state에 함께 반영 (save 시 DB 동기화용)
    const casting = useStoryboardStore.getState().castingRecommendation;
    setState((prev) => ({
      ...prev,
      scenes: finalScenes,
      isGenerating: false,
      progress: null,
      isWaitingForInput: false,
      justGenerated: true,
      ...(casting && {
        structure: casting.structure || prev.structure,
        characterId: casting.character_a_id ?? prev.characterId,
        characterBId: casting.character_b_id ?? prev.characterBId,
        characterName: casting.character_a_name || prev.characterName,
        characterBName: casting.character_b_name || prev.characterBName,
      }),
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
