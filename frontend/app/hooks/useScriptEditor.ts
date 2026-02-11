"use client";

import { useState, useCallback, useRef } from "react";
import axios from "axios";
import { API_BASE, SCRIPTS_LIST_REFRESH } from "../constants";
import { useContextStore } from "../store/useContextStore";
import { useUIStore } from "../store/useUIStore";
import type { Scene } from "../types";

export type SceneItem = {
  id: number;
  order: number;
  script: string;
  speaker: string;
  duration: number;
  image_prompt: string;
  image_prompt_ko: string;
  image_url: string | null;
};

export type ScriptEditorState = {
  topic: string;
  description: string;
  duration: number;
  language: string;
  structure: string;
  characterId: number | null;
  characterBId: number | null;
  scenes: SceneItem[];
  isGenerating: boolean;
  storyboardId: number | null;
  isSaving: boolean;
};

type ScriptEditorActions = ScriptEditorState & {
  setField: <K extends keyof ScriptEditorState>(key: K, value: ScriptEditorState[K]) => void;
  updateScene: (index: number, patch: Partial<SceneItem>) => void;
  generate: () => Promise<void>;
  save: () => Promise<void>;
  loadStoryboard: (id: number) => Promise<void>;
};

type ScriptEditorOptions = {
  onSaved?: (id: number) => void;
};

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
    characterBId: null,
    scenes: [],
    isGenerating: false,
    storyboardId: null,
    isSaving: false,
  });

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
    setState((prev) => ({ ...prev, isGenerating: true }));
    try {
      const body: Record<string, unknown> = {
        topic: state.topic.trim(),
        description: state.description.trim() || undefined,
        duration: state.duration,
        language: state.language,
        structure: state.structure,
        group_id: groupId,
      };
      if (state.characterId) body.character_id = state.characterId;
      if (state.characterBId) body.character_b_id = state.characterBId;

      const res = await axios.post(`${API_BASE}/scripts/generate`, body);
      const data = res.data;
      const scenes: SceneItem[] = (data.scenes ?? []).map((s: Scene, i: number) => ({
        id: s.id ?? i + 1,
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
        scenes,
        storyboardId: data.id ?? prev.storyboardId,
        isGenerating: false,
      }));
      showToast("Script generated", "success");
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? err.message)
        : "Generation failed";
      showToast(String(msg), "error");
      setState((prev) => ({ ...prev, isGenerating: false }));
    }
  }, [
    state.topic,
    state.description,
    state.duration,
    state.language,
    state.structure,
    state.characterId,
    state.characterBId,
    groupId,
    showToast,
  ]);

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
        scenes: state.scenes.map((s) => ({
          script: s.script,
          speaker: s.speaker,
          duration: s.duration,
          image_prompt: s.image_prompt,
          image_prompt_ko: s.image_prompt_ko,
        })),
      };
      if (state.storyboardId) {
        await axios.put(`${API_BASE}/storyboards/${state.storyboardId}`, body);
        useContextStore.getState().setContext({
          storyboardId: state.storyboardId,
          storyboardTitle: state.topic.trim(),
        });
        window.dispatchEvent(new CustomEvent(SCRIPTS_LIST_REFRESH));
        showToast("Script saved", "success");
      } else {
        const res = await axios.post(`${API_BASE}/storyboards`, body);
        const newId = res.data.id;
        setState((prev) => ({ ...prev, storyboardId: newId }));
        useContextStore.getState().setContext({
          storyboardId: newId,
          storyboardTitle: state.topic.trim(),
        });
        window.dispatchEvent(new CustomEvent(SCRIPTS_LIST_REFRESH));
        onSavedRef.current?.(newId);
        showToast("Script created", "success");
      }
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? err.message)
        : "Save failed";
      showToast(String(msg), "error");
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
          characterBId: data.character_b_id ?? null,
          scenes,
          storyboardId: id,
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

  return { ...state, setField, updateScene, generate, save, loadStoryboard };
}
