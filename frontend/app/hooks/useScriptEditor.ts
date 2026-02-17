"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import { useContextStore } from "../store/useContextStore";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useUIStore } from "../store/useUIStore";
import type {
  ConceptCandidate,
  FeedbackPreset,
  PipelineStep,
  Scene,
  ScriptStreamEvent,
} from "../types";
import { generateSceneClientId } from "../utils/uuid";
import { getInitialSteps, updatePipelineSteps } from "../utils/pipelineSteps";

export type SceneItem = {
  id: number;
  client_id: string;
  order: number;
  script: string;
  speaker: string;
  duration: number;
  image_prompt: string;
  image_prompt_ko: string;
  image_url: string | null;
};

export type ScriptProgress = {
  node: string;
  label: string;
  percent: number;
};

export type ScriptEditorState = {
  topic: string;
  description: string;
  duration: number;
  language: string;
  structure: string;
  characterId: number | null;
  characterName: string | null;
  characterBId: number | null;
  characterBName: string | null;
  scenes: SceneItem[];
  isGenerating: boolean;
  progress: ScriptProgress | null;
  storyboardId: number | null;
  storyboardVersion: number | null;
  isSaving: boolean;
  mode: "quick" | "full";
  preset: string | null;
  threadId: string | null;
  isWaitingForInput: boolean;
  isWaitingForConcept: boolean;
  concepts: ConceptCandidate[] | null;
  recommendedConceptId: number | null;
  feedbackSubmitted: boolean;
  justGenerated: boolean;
  references: string;
  feedbackPresets: FeedbackPreset[] | null;
  pipelineSteps: PipelineStep[];
  nodeResults: Record<string, Record<string, unknown>>;
  traceId: string | null;
};

export type ResumeOptions = {
  feedbackPreset?: string;
  feedbackPresetParams?: Record<string, string>;
  customConcept?: { title: string; concept: string };
};

export type ScriptEditorActions = ScriptEditorState & {
  setField: <K extends keyof ScriptEditorState>(key: K, value: ScriptEditorState[K]) => void;
  updateScene: (index: number, patch: Partial<SceneItem>) => void;
  generate: () => Promise<void>;
  resume: (
    action: "approve" | "revise" | "select" | "regenerate" | "custom_concept",
    feedback?: string,
    conceptId?: number,
    options?: ResumeOptions
  ) => Promise<void>;
  submitFeedback: (rating: "positive" | "negative", feedbackText?: string) => Promise<void>;
  save: () => Promise<void>;
  loadStoryboard: (id: number) => Promise<void>;
  reset: () => void;
};

type ScriptEditorOptions = {
  onSaved?: (id: number) => void;
};

function mapEventScenes(scenes: Scene[]): SceneItem[] {
  return scenes.map((s, i) => ({
    id: s.id ?? i + 1,
    client_id: generateSceneClientId(),
    order: s.order ?? i + 1,
    script: s.script ?? "",
    speaker: s.speaker ?? "Narrator",
    duration: s.duration ?? 3,
    image_prompt: s.image_prompt ?? "",
    image_prompt_ko: s.image_prompt_ko ?? "",
    image_url: s.image_url ?? null,
  }));
}

type SyncMeta = {
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
function syncToGlobalStore(scenes: SceneItem[], meta: SyncMeta) {
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

async function parseSSEStream(
  response: Response,
  onEvent: (event: ScriptStreamEvent) => void
): Promise<void> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      if (part.startsWith("data: ")) {
        onEvent(JSON.parse(part.slice(6)));
      }
    }
  }
}

type StreamResult = { finalScenes: SceneItem[] | null; isWaiting: boolean };

/** Common SSE stream processing for generate & resume. */
async function processSSEStream(
  response: Response,
  setState: React.Dispatch<React.SetStateAction<ScriptEditorState>>,
  options?: { trackThreadId?: boolean }
): Promise<StreamResult> {
  let finalScenes: SceneItem[] | null = null;
  let isWaiting = false;

  await parseSSEStream(response, (event: ScriptStreamEvent) => {
    setState((prev) => {
      const nextSteps = updatePipelineSteps(prev.pipelineSteps, event, prev.mode);
      const nextNodeResults = event.node_result
        ? { ...prev.nodeResults, [event.node]: event.node_result as Record<string, unknown> }
        : prev.nodeResults;
      return {
        ...prev,
        progress: { node: event.node, label: event.label, percent: event.percent },
        pipelineSteps: nextSteps,
        nodeResults: nextNodeResults,
      };
    });

    if (options?.trackThreadId && event.thread_id) {
      setState((prev) => ({ ...prev, threadId: event.thread_id! }));
    }
    if (event.trace_id) {
      setState((prev) => ({ ...prev, traceId: event.trace_id! }));
    }

    if (event.status === "completed" && event.result?.scenes) {
      finalScenes = mapEventScenes(event.result.scenes);
    }

    if (event.status === "waiting_for_input") {
      isWaiting = true;
      if (event.node === "concept_gate" && event.result?.candidates) {
        // 컨셉 선택 대기
        const candidates = event.result.candidates;
        const selected = event.result.selected_concept;
        const recIdx = selected
          ? candidates.findIndex((c) => c.agent_role === selected.agent_role)
          : 0;
        setState((prev) => ({
          ...prev,
          concepts: candidates,
          recommendedConceptId: recIdx >= 0 ? recIdx : 0,
          isGenerating: false,
          isWaitingForConcept: true,
        }));
      } else {
        // human_gate 리뷰 승인 대기 — review_result도 nodeResults에 저장
        const draftScenes = event.result?.scenes ? mapEventScenes(event.result.scenes) : [];
        setState((prev) => {
          const nr = event.result?.review_result
            ? { ...prev.nodeResults, review: event.result.review_result as Record<string, unknown> }
            : prev.nodeResults;
          return {
            ...prev,
            scenes: draftScenes.length > 0 ? draftScenes : prev.scenes,
            isGenerating: false,
            isWaitingForInput: true,
            nodeResults: nr,
          };
        });
      }
    }

    if (event.status === "error") {
      throw new Error(event.error ?? "Stream failed");
    }
  });

  return { finalScenes, isWaiting };
}

export function useScriptEditor(options?: ScriptEditorOptions): ScriptEditorActions {
  const groupId = useContextStore((s) => s.groupId);
  const showToast = useUIStore((s) => s.showToast);
  const onSavedRef = useRef(options?.onSaved);
  onSavedRef.current = options?.onSaved;

  const [state, setState] = useState<ScriptEditorState>({
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
    mode: "quick",
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
  });

  // Lazy-fetch feedback presets when waiting for input
  useEffect(() => {
    if (!state.isWaitingForInput || state.feedbackPresets) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await axios.get(`${API_BASE}/scripts/feedback-presets`);
        if (!cancelled) {
          setState((prev) => ({ ...prev, feedbackPresets: res.data.presets }));
        }
      } catch {
        // silent — presets are optional enhancement
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [state.isWaitingForInput, state.feedbackPresets]);

  const setField = useCallback(
    <K extends keyof ScriptEditorState>(key: K, value: ScriptEditorState[K]) => {
      setState((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const updateScene = useCallback((index: number, patch: Partial<SceneItem>) => {
    setState((prev) => {
      const next = [...prev.scenes];
      next[index] = { ...next[index], ...patch };
      return { ...prev, scenes: next };
    });
  }, []);

  const generate = useCallback(async () => {
    if (!state.topic.trim()) return;
    setState((prev) => ({
      ...prev,
      isGenerating: true,
      progress: null,
      justGenerated: false,
      pipelineSteps: getInitialSteps(prev.mode),
      nodeResults: {},
    }));

    const body: Record<string, unknown> = {
      topic: state.topic.trim(),
      description: state.description.trim() || undefined,
      duration: state.duration,
      language: state.language,
      structure: state.structure,
      group_id: groupId,
      mode: state.mode,
    };
    if (state.preset) body.preset = state.preset;
    if (state.characterId) body.character_id = state.characterId;
    if (state.characterBId) body.character_b_id = state.characterBId;
    const refs = state.references.trim();
    if (refs) {
      body.references = refs
        .split("\n")
        .map((r) => r.trim())
        .filter(Boolean);
    }

    try {
      const response = await fetch(`${API_BASE}/scripts/generate-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail ?? `HTTP ${response.status}`);
      }

      const { finalScenes, isWaiting } = await processSSEStream(response, setState, {
        trackThreadId: true,
      });

      if (isWaiting) {
        // Human gate active — keep isWaitingForInput, don't show toast
      } else if (finalScenes) {
        setState((prev) => ({
          ...prev,
          scenes: finalScenes,
          isGenerating: false,
          progress: null,
          justGenerated: true,
        }));
        // Sync to global store so AutoRun preflight sees scenes immediately
        syncToGlobalStore(finalScenes, {
          topic: state.topic.trim(),
          description: state.description.trim(),
          duration: state.duration,
          language: state.language,
          structure: state.structure,
          characterId: state.characterId,
          characterName: state.characterName,
          characterBId: state.characterBId,
          characterBName: state.characterBName,
        });
        showToast("Script generated", "success");
      } else {
        setState((prev) => ({ ...prev, isGenerating: false, progress: null }));
        showToast("No scenes returned", "warning");
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Generation failed";
      showToast(String(msg), "error");
      setState((prev) => ({ ...prev, isGenerating: false, progress: null }));
    }
  }, [
    state.topic,
    state.description,
    state.duration,
    state.language,
    state.structure,
    state.characterId,
    state.characterBId,
    state.references,
    state.mode,
    state.preset,
    groupId,
    showToast,
  ]);

  const resume = useCallback(
    async (
      action: "approve" | "revise" | "select" | "regenerate" | "custom_concept",
      feedback?: string,
      conceptId?: number,
      options?: ResumeOptions
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

        const { finalScenes, isWaiting } = await processSSEStream(response, setState);

        if (isWaiting) {
          // Human gate active — keep isWaitingForInput
        } else if (finalScenes) {
          setState((prev) => ({
            ...prev,
            scenes: finalScenes,
            isGenerating: false,
            progress: null,
            isWaitingForInput: false,
            justGenerated: true,
          }));
          syncToGlobalStore(finalScenes, {
            topic: state.topic.trim(),
            description: state.description.trim(),
            duration: state.duration,
            language: state.language,
            structure: state.structure,
            characterId: state.characterId,
            characterName: state.characterName,
            characterBId: state.characterBId,
            characterBName: state.characterBName,
          });
          showToast("Script generated", "success");
        } else {
          setState((prev) => ({
            ...prev,
            isGenerating: false,
            progress: null,
          }));
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Resume failed";
        showToast(String(msg), "error");
        setState((prev) => ({
          ...prev,
          isGenerating: false,
          progress: null,
        }));
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
    try {
      const body = {
        title: state.topic.trim(),
        description: state.description.trim() || undefined,
        duration: state.duration,
        language: state.language,
        structure: state.structure,
        group_id: groupId,
        character_id: state.characterId,
        character_b_id: state.characterBId,
        version: state.storyboardVersion ?? undefined,
        scenes: state.scenes.map((s, i) => ({
          scene_id: i,
          client_id: s.client_id,
          script: s.script,
          speaker: s.speaker,
          duration: s.duration,
          image_prompt: s.image_prompt,
          image_prompt_ko: s.image_prompt_ko,
        })),
      };
      const storeMeta: SyncMeta = {
        topic: state.topic.trim(),
        description: state.description.trim(),
        duration: state.duration,
        language: state.language,
        structure: state.structure,
        characterId: state.characterId,
        characterName: state.characterName,
        characterBId: state.characterBId,
        characterBName: state.characterBName,
      };

      if (state.storyboardId) {
        const res = await axios.put(`${API_BASE}/storyboards/${state.storyboardId}`, body);
        setState((prev) => ({ ...prev, storyboardVersion: res.data.version }));
        useContextStore.getState().setContext({
          storyboardId: state.storyboardId,
          storyboardTitle: state.topic.trim(),
        });
        syncToGlobalStore(state.scenes, storeMeta);
        showToast("Script saved", "success");
      } else {
        const res = await axios.post(`${API_BASE}/storyboards`, body);
        const newId = res.data.storyboard_id;
        setState((prev) => ({
          ...prev,
          storyboardId: newId,
          storyboardVersion: res.data.version ?? 1,
        }));
        useContextStore.getState().setContext({
          storyboardId: newId,
          storyboardTitle: state.topic.trim(),
        });
        syncToGlobalStore(state.scenes, storeMeta);
        onSavedRef.current?.(newId);
        showToast("Script created", "success");
      }
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        showToast("다른 탭에서 수정되었습니다. 다시 저장해주세요.", "error");
        // Sync version from server so next save uses correct version
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
        const scenes: SceneItem[] = (data.scenes ?? []).map((s: Scene, i: number) => ({
          id: s.id ?? i + 1,
          client_id: s.client_id ?? generateSceneClientId(),
          order: s.order ?? i + 1,
          script: s.script ?? "",
          speaker: s.speaker ?? "Narrator",
          duration: s.duration ?? 3,
          image_prompt: s.image_prompt ?? "",
          image_prompt_ko: s.image_prompt_ko ?? "",
          image_url: s.image_url ?? null,
        }));
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
          scenes,
          storyboardId: id,
          storyboardVersion: data.version ?? null,
        }));
        useContextStore.getState().setContext({
          storyboardId: id,
          storyboardTitle: data.title ?? "",
        });
      } catch (err) {
        showToast("Failed to load storyboard", "error");
        console.error("[useScriptEditor] loadStoryboard error:", err);
      }
    },
    [showToast]
  );

  const reset = useCallback(() => {
    setState({
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
      mode: "quick",
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
    });
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
