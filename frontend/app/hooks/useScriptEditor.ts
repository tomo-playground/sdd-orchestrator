"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import { useContextStore } from "../store/useContextStore";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useUIStore } from "../store/useUIStore";
import { getInitialSteps } from "../utils/pipelineSteps";
import {
  syncToGlobalStore,
  processSSEStream,
  buildSyncMeta,
  buildGenerateBody,
  buildSavePayload,
  handleStreamOutcome,
  mapLoadedScenes,
} from "./scriptEditor";
import type {
  SceneItem,
  ScriptEditorState,
  ScriptEditorActions,
  ScriptEditorOptions,
  ResumeAction,
  ResumeOptions,
} from "./scriptEditor";

// Re-export types for backward compat
export type {
  SceneItem,
  ScriptProgress,
  ScriptEditorState,
  ResumeAction,
  ResumeOptions,
  ScriptEditorActions,
} from "./scriptEditor";

/** Fields that represent user content — changes should mark global store dirty. */
const CONTENT_FIELDS: ReadonlySet<string> = new Set([
  "topic",
  "description",
  "duration",
  "language",
  "structure",
  "characterId",
  "characterName",
  "characterBId",
  "characterBName",
  "references",
]);

const INITIAL_STATE: ScriptEditorState = {
  topic: "",
  description: "",
  duration: 30,
  language: "korean",
  structure: "monologue",
  characterId: null,
  characterName: null,
  characterBId: null,
  characterBName: null,
  scenes: [],
  isGenerating: false,
  progress: null,
  storyboardId: null,
  storyboardVersion: null,
  isSaving: false,
  directorSkipStages: [],
  threadId: null,
  isWaitingForInput: false,
  isWaitingForConcept: false,
  concepts: null,
  recommendedConceptId: null,
  references: "",
  feedbackSubmitted: false,
  justGenerated: false,
  feedbackPresets: null,
  pipelineSteps: [],
  nodeResults: {},
  traceId: null,
  productionSnapshot: null,
  interactionMode: "guided",
  isWaitingForPlan: false,
  isWaitingForIntake: false,
  intakeData: null,
  chatContext: [],
};

export function useScriptEditor(options?: ScriptEditorOptions): ScriptEditorActions {
  const groupId = useContextStore((s) => s.groupId);
  const showToast = useUIStore((s) => s.showToast);
  const onSavedRef = useRef(options?.onSaved);
  onSavedRef.current = options?.onSaved;
  const onNodeEventRef = useRef(options?.onNodeEvent);
  onNodeEventRef.current = options?.onNodeEvent;

  const [state, setState] = useState<ScriptEditorState>({ ...INITIAL_STATE });

  const stateRef = useRef(state);
  stateRef.current = state;
  const dirtyRef = useRef(false);
  const streamAbortRef = useRef<AbortController | null>(null);

  // Sync to global store on unmount
  useEffect(() => {
    return () => {
      if (!dirtyRef.current) return;
      const s = stateRef.current;
      if (!s.topic.trim() && s.scenes.length === 0) return;
      syncToGlobalStore(s.scenes, buildSyncMeta(s));
    };
  }, []);

  // Lazy-fetch feedback presets when waiting for input
  useEffect(() => {
    if (!state.isWaitingForInput || state.feedbackPresets) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await axios.get(`${API_BASE}/scripts/feedback-presets`);
        if (!cancelled) setState((prev) => ({ ...prev, feedbackPresets: res.data.presets }));
      } catch {
        /* silent */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [state.isWaitingForInput, state.feedbackPresets]);

  const setField = useCallback(
    <K extends keyof ScriptEditorState>(key: K, value: ScriptEditorState[K]) => {
      setState((prev) => ({ ...prev, [key]: value }));
      if (CONTENT_FIELDS.has(key as string)) {
        dirtyRef.current = true;
        // topic/description은 글로벌 스토어에 즉시 동기화 — persistStoryboard가 읽을 수 있도록
        const syncPayload: Record<string, unknown> = { isDirty: true };
        if (key === "topic") syncPayload.topic = value;
        if (key === "description") syncPayload.description = value;
        useStoryboardStore.getState().set(syncPayload);
      }
    },
    []
  );

  const updateScene = useCallback((index: number, patch: Partial<SceneItem>) => {
    setState((prev) => {
      const next = [...prev.scenes];
      next[index] = { ...next[index], ...patch };
      return { ...prev, scenes: next };
    });
    dirtyRef.current = true;
    useStoryboardStore.getState().set({ isDirty: true });
    // Sync updated scenes to global store for autoSave
    queueMicrotask(() => {
      const s = stateRef.current;
      syncToGlobalStore(s.scenes, buildSyncMeta(s));
    });
  }, []);

  const generate = useCallback(async () => {
    // stateRef.current를 통해 항상 최신 state를 읽어 stale closure 방지
    const currentState = stateRef.current;
    if (!currentState.topic.trim()) return;
    streamAbortRef.current?.abort();
    const controller = new AbortController();
    streamAbortRef.current = controller;
    useStoryboardStore.getState().set({ isScriptGenerating: true });
    setState((prev) => ({
      ...prev,
      isGenerating: true,
      progress: null,
      justGenerated: false,
      pipelineSteps: getInitialSteps(),
      nodeResults: {},
    }));
    try {
      const response = await fetch(`${API_BASE}/scripts/generate-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildGenerateBody(currentState, groupId)),
        signal: controller.signal,
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail ?? `HTTP ${response.status}`);
      }
      const result = await processSSEStream(response, setState, {
        trackThreadId: true,
        onNodeEvent: onNodeEventRef.current,
      });
      // SSE error가 onNodeEvent로 이미 처리된 경우 (채팅 ErrorCard 표시됨) → toast 생략
      if (result.hasError) {
        setState((prev) => ({ ...prev, isGenerating: false, progress: null }));
        return;
      }
      handleStreamOutcome({
        ...result,
        meta: buildSyncMeta(stateRef.current),
        setState,
        dirtyRef,
        showToast,
      });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      showToast(err instanceof Error ? err.message : "Generation failed", "error");
      setState((prev) => ({ ...prev, isGenerating: false, progress: null }));
    } finally {
      useStoryboardStore.getState().set({ isScriptGenerating: false });
      streamAbortRef.current = null;
    }
  }, [groupId, showToast]);

  const resume = useCallback(
    async (
      action: ResumeAction,
      feedback?: string,
      conceptId?: number,
      options?: ResumeOptions
    ) => {
      if (!stateRef.current.threadId) return;
      streamAbortRef.current?.abort();
      const controller = new AbortController();
      streamAbortRef.current = controller;
      useStoryboardStore.getState().set({ isScriptGenerating: true });
      setState((prev) => ({
        ...prev,
        isGenerating: true,
        isWaitingForInput: false,
        isWaitingForConcept: false,
        isWaitingForPlan: false,
        isWaitingForIntake: false,
        intakeData: null,
        concepts: null,
        recommendedConceptId: null,
        progress: null,
      }));
      try {
        const body: Record<string, unknown> = {
          thread_id: stateRef.current.threadId,
          action,
          feedback,
          trace_id: stateRef.current.traceId || undefined,
          storyboard_id: stateRef.current.storyboardId || undefined,
        };
        if (conceptId !== undefined) body.concept_id = conceptId;
        if (options?.feedbackPreset) body.feedback_preset = options.feedbackPreset;
        if (options?.feedbackPresetParams)
          body.feedback_preset_params = options.feedbackPresetParams;
        if (options?.customConcept) body.custom_concept = options.customConcept;
        if (options?.intakeValue) body.intake_value = options.intakeValue;

        const response = await fetch(`${API_BASE}/scripts/resume`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const result = await processSSEStream(response, setState, {
          onNodeEvent: onNodeEventRef.current,
        });
        // SSE error가 onNodeEvent로 이미 처리된 경우 (채팅 ErrorCard 표시됨) → toast 생략
        if (result.hasError) {
          setState((prev) => ({ ...prev, isGenerating: false, progress: null }));
          return;
        }
        const meta = buildSyncMeta(stateRef.current);
        if (
          !handleStreamOutcome({ ...result, meta, setState, dirtyRef, showToast }) &&
          !result.isWaiting
        ) {
          showToast("대본 생성이 완료되지 않았습니다", "warning");
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        showToast(err instanceof Error ? err.message : "Resume failed", "error");
        setState((prev) => ({ ...prev, isGenerating: false, progress: null }));
      } finally {
        useStoryboardStore.getState().set({ isScriptGenerating: false });
        streamAbortRef.current = null;
      }
    },
    [showToast]
  );

  const submitFeedback = useCallback(
    async (rating: "positive" | "negative", feedbackText?: string) => {
      try {
        await fetch(`${API_BASE}/scripts/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            thread_id: stateRef.current.threadId,
            storyboard_id: stateRef.current.storyboardId,
            rating,
            feedback_text: feedbackText || undefined,
          }),
        });
        setState((prev) => ({ ...prev, feedbackSubmitted: true }));
        showToast("피드백이 저장되었습니다", "success");
      } catch {
        showToast("피드백 저장 실패", "error");
      }
    },
    [showToast]
  );

  const save = useCallback(async () => {
    setState((prev) => ({ ...prev, isSaving: true }));
    const current = stateRef.current;
    const body = buildSavePayload(current, groupId);
    const storeMeta = buildSyncMeta(current);
    try {
      const isUpdate = !!current.storyboardId;
      const res = isUpdate
        ? await axios.put(`${API_BASE}/storyboards/${current.storyboardId}`, body)
        : await axios.post(`${API_BASE}/storyboards`, body);
      const resolvedId = isUpdate ? current.storyboardId! : res.data.storyboard_id;
      setState((prev) => ({
        ...prev,
        storyboardId: resolvedId,
        storyboardVersion: res.data.version ?? (isUpdate ? prev.storyboardVersion : 1),
      }));
      useContextStore.getState().setContext({
        storyboardId: resolvedId,
        storyboardTitle: current.topic.trim(),
      });
      syncToGlobalStore(current.scenes, storeMeta);
      if (!isUpdate) onSavedRef.current?.(resolvedId);
      dirtyRef.current = false;
      useStoryboardStore.getState().set({ isDirty: false });
      showToast("스크립트 저장 완료", "success");
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        showToast("다른 탭에서 수정되었습니다. 다시 저장해주세요.", "error");
        if (stateRef.current.storyboardId) {
          try {
            const fresh = await axios.get(
              `${API_BASE}/storyboards/${stateRef.current.storyboardId}`
            );
            setState((prev) => ({ ...prev, storyboardVersion: fresh.data.version ?? null }));
          } catch {
            /* silent */
          }
        }
      } else {
        const msg = axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? err.message)
          : "저장 실패";
        showToast(String(msg), "error");
      }
    } finally {
      setState((prev) => ({ ...prev, isSaving: false }));
    }
  }, [groupId, showToast]);

  const loadStoryboard = useCallback(
    async (id: number) => {
      try {
        const res = await axios.get(`${API_BASE}/storyboards/${id}`);
        const data = res.data;
        setState((prev) => {
          // 다른 스토리보드 전환 시 DB 값 사용, 같은 ID 재로드(Draft 직후)는 기존 값 보존
          const isSwitching = prev.storyboardId !== null && prev.storyboardId !== id;
          return {
            ...prev,
            topic: isSwitching ? (data.title ?? "") : prev.topic || data.title || "",
            description: isSwitching
              ? (data.description ?? "")
              : prev.description || data.description || "",
            duration: data.duration ?? 30,
            language: data.language ?? "korean",
            structure: data.structure ?? "monologue",
            characterId: data.character_id ?? null,
            characterName: data.character_name ?? null,
            characterBId: data.character_b_id ?? null,
            characterBName: data.character_b_name ?? null,
            scenes: mapLoadedScenes(data.scenes ?? []),
            storyboardId: id,
            storyboardVersion: data.version ?? null,
            chatContext: [],
          };
        });
        dirtyRef.current = false;
        useContextStore
          .getState()
          .setContext({ storyboardId: id, storyboardTitle: data.title ?? "" });
      } catch (err) {
        showToast("영상 로드에 실패했습니다", "error");
        console.error("[useScriptEditor] loadStoryboard error:", err);
      }
    },
    [showToast]
  );

  const reset = useCallback(() => {
    dirtyRef.current = false;
    setState({ ...INITIAL_STATE });
  }, []);

  const cancel = useCallback(() => {
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    setState((prev) => ({ ...prev, isGenerating: false, progress: null }));
  }, []);

  return {
    ...state,
    setField,
    updateScene,
    generate,
    resume,
    submitFeedback,
    save,
    loadStoryboard,
    reset,
    cancel,
  };
}
