import type React from "react";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useContextStore } from "../../store/useContextStore";
import { syncToGlobalStore } from "./mappers";
import { initializeVideoMetadata } from "../../store/actions/outputActions";
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
  const { storyboardId } = useContextStore.getState();
  const body: Record<string, unknown> = {
    topic: s.topic.trim(),
    description: s.description.trim() || undefined,
    duration: s.duration,
    language: s.language,
    group_id: groupId,
    storyboard_id: storyboardId ?? undefined,
    interaction_mode: s.interactionMode,
    // analyze-topic에서 추천된 structure가 있으면 전달 (Director 힌트)
    ...(s.structure && { structure: s.structure }),
    // FastTrack: Director 건너뛰므로 캐릭터/skip_stages를 직접 전달
    // Full: character_id는 Director 캐스팅 SSOT이므로 미전달
    // skip_stages는 Backend SSOT (/presets → useStoryboardStore.fastTrackSkipStages)
    ...(s.fastTrack && {
      skip_stages: useStoryboardStore.getState().fastTrackSkipStages,
      ...(s.characterId && { character_id: s.characterId }),
      ...(s.characterBId && { character_b_id: s.characterBId }),
    }),
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
  /** SSE completion에서 전달된 캐릭터 ID (Full/FastTrack 공통) */
  characterId?: number | null;
  characterBId?: number | null;
  /** Backend에서 결정된 structure (e.g. dialogue, monologue) */
  structure?: string | null;
  /** Backend warnings (e.g. TTS Designer fallback) */
  warnings?: string[];
};

/** Shared post-stream handler for generate & resume. Returns true if scenes were produced. */
export function handleStreamOutcome(opts: StreamOutcomeOpts): boolean {
  const { finalScenes, isWaiting, meta, setState, dirtyRef, showToast } = opts;
  if (isWaiting) return false;
  if (finalScenes) {
    // 캐릭터 해결: casting(Full: inventory_resolve) > completion(공통: SSE result)
    const casting = useStoryboardStore.getState().castingRecommendation;
    const resolvedCharId = casting?.character_a_id ?? opts.characterId ?? null;
    const resolvedCharBId = casting?.character_b_id ?? opts.characterBId ?? null;
    const resolvedCharName = casting?.character_a_name || null;
    const resolvedCharBName = casting?.character_b_name || null;
    const resolvedStructure = casting?.structure || opts.structure || null;

    setState((prev) => ({
      ...prev,
      scenes: finalScenes,
      isGenerating: false,
      progress: null,
      isWaitingForInput: false,
      justGenerated: true,
      ...(resolvedStructure && { structure: resolvedStructure }),
      ...(resolvedCharId && { characterId: resolvedCharId }),
      ...(resolvedCharBId && { characterBId: resolvedCharBId }),
      ...(resolvedCharName && { characterName: resolvedCharName }),
      ...(resolvedCharBName && { characterBName: resolvedCharBName }),
    }));
    const syncMeta = {
      ...meta,
      ...(resolvedStructure && { structure: resolvedStructure }),
      ...(resolvedCharId && { characterId: resolvedCharId }),
      ...(resolvedCharBId && { characterBId: resolvedCharBId }),
      ...(resolvedCharName && { characterName: resolvedCharName }),
      ...(resolvedCharBName && { characterBName: resolvedCharBName }),
    };
    syncToGlobalStore(finalScenes, syncMeta);
    dirtyRef.current = true;
    useStoryboardStore.getState().set({
      isDirty: true,
      ...(casting && { castingRecommendation: null }),
    });
    // 파이프라인 완료 후 실제 topic으로 캡션 재생성 (Draft 타이틀로 잘못 생성된 캡션 교체)
    if (meta.topic) {
      void initializeVideoMetadata(meta.topic, true);
    }
    showToast("스크립트 생성 완료", "success");
    // Backend warnings 토스트 (e.g. TTS Designer fallback)
    if (opts.warnings?.length) {
      for (const w of opts.warnings) {
        showToast(w, "warning");
      }
    }
    return true;
  }
  setState((prev) => ({ ...prev, isGenerating: false, progress: null }));
  showToast("생성된 씬이 없습니다", "warning");
  return false;
}
