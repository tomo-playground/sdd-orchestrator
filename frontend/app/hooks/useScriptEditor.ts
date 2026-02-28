"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import { useContextStore } from "../store/useContextStore";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useUIStore } from "../store/useUIStore";
import { EXPRESS_SKIP_STAGES, getInitialSteps } from "../utils/pipelineSteps";
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
} from "./scriptEditor";

// Re-export types for backward compat
export type {
  SceneItem,
  ScriptProgress,
  ScriptEditorState,
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
  "preset",
  "skipStages",
]);

const INITIAL_STATE: ScriptEditorState = {
  topic: "",
  description: "",
  duration: 30,
  language: "Korean",
  structure: "Monologue",
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
  skipStages: [...EXPRESS_SKIP_STAGES],
  preset: null,
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
        useStoryboardStore.getState().set({ isDirty: true });
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
  }, []);

  const generate = useCallback(async () => {
    // stateRef.current를 통해 항상 최신 state를 읽어 stale closure 방지
    const currentState = stateRef.current;
    if (!currentState.topic.trim()) return;
    useStoryboardStore.getState().set({ castingRecommendation: null });
    setState((prev) => ({
      ...prev,
      isGenerating: true,
      progress: null,
      justGenerated: false,
      pipelineSteps: getInitialSteps(prev.skipStages),
      nodeResults: {},
    }));
    try {
      const response = await fetch(`${API_BASE}/scripts/generate-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildGenerateBody(currentState, groupId)),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail ?? `HTTP ${response.status}`);
      }
      const result = await processSSEStream(response, setState, {
        trackThreadId: true,
        onNodeEvent: onNodeEventRef.current,
      });
      handleStreamOutcome({
        ...result,
        meta: buildSyncMeta(stateRef.current),
        setState,
        dirtyRef,
        showToast,
      });
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Generation failed", "error");
      setState((prev) => ({ ...prev, isGenerating: false, progress: null }));
    }
  }, [groupId, showToast]);

  const resume = useCallback(
    async (
      action: "approve" | "revise" | "select" | "regenerate" | "custom_concept",
      feedback?: string,
      conceptId?: number,
      options?: {
        feedbackPreset?: string;
        feedbackPresetParams?: Record<string, string>;
        customConcept?: { title: string; concept: string };
      }
    ) => {
      if (!state.threadId) return;
      setState((prev) => ({
        ...prev,
        isGenerating: true,
        isWaitingForInput: false,
        isWaitingForConcept: false,
        concepts: null,
        recommendedConceptId: null,
        progress: null,
      }));
      try {
        const body: Record<string, unknown> = {
          thread_id: state.threadId,
          action,
          feedback,
          trace_id: state.traceId || undefined,
        };
        if (conceptId !== undefined) body.concept_id = conceptId;
        if (options?.feedbackPreset) body.feedback_preset = options.feedbackPreset;
        if (options?.feedbackPresetParams)
          body.feedback_preset_params = options.feedbackPresetParams;
        if (options?.customConcept) body.custom_concept = options.customConcept;

        const response = await fetch(`${API_BASE}/scripts/resume`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const result = await processSSEStream(response, setState, {
          onNodeEvent: onNodeEventRef.current,
        });
        const meta = buildSyncMeta(stateRef.current);
        if (
          !handleStreamOutcome({ ...result, meta, setState, dirtyRef, showToast }) &&
          !result.isWaiting
        ) {
          showToast("대본 생성이 완료되지 않았습니다", "warning");
        }
      } catch (err) {
        showToast(err instanceof Error ? err.message : "Resume failed", "error");
        setState((prev) => ({ ...prev, isGenerating: false, progress: null }));
      }
    },
    [state.threadId, state.traceId, showToast]
  );

  const submitFeedback = useCallback(
    async (rating: "positive" | "negative", feedbackText?: string) => {
      try {
        await fetch(`${API_BASE}/scripts/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            thread_id: state.threadId,
            storyboard_id: state.storyboardId,
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
    [state.threadId, state.storyboardId, showToast]
  );

  const save = useCallback(async () => {
    setState((prev) => ({ ...prev, isSaving: true }));
    const body = buildSavePayload(state, groupId);
    const storeMeta = buildSyncMeta(state);
    try {
      if (state.storyboardId) {
        const res = await axios.put(`${API_BASE}/storyboards/${state.storyboardId}`, body);
        setState((prev) => ({ ...prev, storyboardVersion: res.data.version }));
        useContextStore
          .getState()
          .setContext({ storyboardId: state.storyboardId, storyboardTitle: state.topic.trim() });
      } else {
        const res = await axios.post(`${API_BASE}/storyboards`, body);
        const newId = res.data.storyboard_id;
        setState((prev) => ({
          ...prev,
          storyboardId: newId,
          storyboardVersion: res.data.version ?? 1,
        }));
        useContextStore
          .getState()
          .setContext({ storyboardId: newId, storyboardTitle: state.topic.trim() });
        onSavedRef.current?.(newId);
      }
      syncToGlobalStore(state.scenes, storeMeta);
      dirtyRef.current = false;
      useStoryboardStore.getState().set({ isDirty: false });
      showToast(state.storyboardId ? "Script saved" : "Script created", "success");
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        showToast("다른 탭에서 수정되었습니다. 다시 저장해주세요.", "error");
        if (state.storyboardId) {
          try {
            const fresh = await axios.get(`${API_BASE}/storyboards/${state.storyboardId}`);
            setState((prev) => ({ ...prev, storyboardVersion: fresh.data.version ?? null }));
          } catch {
            /* silent */
          }
        }
      } else {
        const msg = axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? err.message)
          : "Save failed";
        showToast(String(msg), "error");
      }
    } finally {
      setState((prev) => ({ ...prev, isSaving: false }));
    }
  }, [state, groupId, showToast]);

  const loadStoryboard = useCallback(
    async (id: number) => {
      try {
        const res = await axios.get(`${API_BASE}/storyboards/${id}`);
        const data = res.data;
        setState((prev) => ({
          ...prev,
          topic: data.title ?? "",
          description: data.description ?? "",
          duration: data.duration ?? 30,
          language: data.language ?? "Korean",
          structure: data.structure ?? "Monologue",
          characterId: data.character_id ?? null,
          characterName: data.character_name ?? null,
          characterBId: data.character_b_id ?? null,
          characterBName: data.character_b_name ?? null,
          scenes: mapLoadedScenes(data.scenes ?? []),
          storyboardId: id,
          storyboardVersion: data.version ?? null,
        }));
        dirtyRef.current = false;
        useContextStore
          .getState()
          .setContext({ storyboardId: id, storyboardTitle: data.title ?? "" });
      } catch (err) {
        showToast("Failed to load storyboard", "error");
        console.error("[useScriptEditor] loadStoryboard error:", err);
      }
    },
    [showToast]
  );

  const reset = useCallback(() => {
    dirtyRef.current = false;
    setState({ ...INITIAL_STATE });
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
  };
}
