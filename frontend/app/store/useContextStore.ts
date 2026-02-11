import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { ProjectItem, GroupItem } from "../types";

export interface ContextState {
  // Persisted
  projectId: number | null;
  groupId: number | null;
  storyboardId: number | null;
  storyboardTitle: string;

  // Transient (re-fetched on mount)
  projects: ProjectItem[];
  groups: GroupItem[];
  isLoadingProjects: boolean;
  isLoadingGroups: boolean;

  // Effective config (runtime-derived from group/project)
  effectivePresetName: string | null;
  effectivePresetSource: string | null;
  effectiveStyleProfileId: number | null;
  effectiveCharacterId: number | null;
  effectiveConfigLoaded: boolean;
  effectiveSdSteps: number | null;
  effectiveSdCfgScale: number | null;
  effectiveSdSamplerName: string | null;
  effectiveSdClipSkip: number | null;

  // Actions
  setContext: (
    updates: Partial<
      Pick<ContextState, "projectId" | "groupId" | "storyboardId" | "storyboardTitle">
    >
  ) => void;
  setProjects: (projects: ProjectItem[]) => void;
  setGroups: (groups: GroupItem[]) => void;
  setContextLoading: (
    updates: Partial<Pick<ContextState, "isLoadingProjects" | "isLoadingGroups">>
  ) => void;
  setEffectivePreset: (name: string | null, source: string | null) => void;
  setEffectiveDefaults: (styleId: number | null, charId: number | null, loaded: boolean) => void;
  setEffectiveSdParams: (params: {
    steps: number | null;
    cfgScale: number | null;
    samplerName: string | null;
    clipSkip: number | null;
  }) => void;
  resetContext: () => void;
}

const CONTEXT_STORE_KEY = "shorts-producer:context:v1";

const TRANSIENT_CONTEXT_KEYS: (keyof ContextState)[] = [
  "projects",
  "groups",
  "isLoadingProjects",
  "isLoadingGroups",
  "effectivePresetName",
  "effectivePresetSource",
  "effectiveStyleProfileId",
  "effectiveCharacterId",
  "effectiveConfigLoaded",
  "effectiveSdSteps",
  "effectiveSdCfgScale",
  "effectiveSdSamplerName",
  "effectiveSdClipSkip",
];

export const useContextStore = create<ContextState>()(
  persist(
    (set) => ({
      projectId: null,
      groupId: null,
      storyboardId: null,
      storyboardTitle: "",
      projects: [],
      groups: [],
      isLoadingProjects: false,
      isLoadingGroups: false,
      effectivePresetName: null,
      effectivePresetSource: null,
      effectiveStyleProfileId: null,
      effectiveCharacterId: null,
      effectiveConfigLoaded: false,
      effectiveSdSteps: null,
      effectiveSdCfgScale: null,
      effectiveSdSamplerName: null,
      effectiveSdClipSkip: null,

      setContext: (updates) => set((s) => ({ ...s, ...updates })),
      setProjects: (projects) => set({ projects }),
      setGroups: (groups) => set({ groups }),
      setContextLoading: (updates) => set((s) => ({ ...s, ...updates })),
      setEffectivePreset: (name, source) =>
        set({ effectivePresetName: name, effectivePresetSource: source }),
      setEffectiveDefaults: (styleId, charId, loaded) =>
        set({
          effectiveStyleProfileId: styleId,
          effectiveCharacterId: charId,
          effectiveConfigLoaded: loaded,
        }),
      setEffectiveSdParams: (params) =>
        set({
          effectiveSdSteps: params.steps,
          effectiveSdCfgScale: params.cfgScale,
          effectiveSdSamplerName: params.samplerName,
          effectiveSdClipSkip: params.clipSkip,
        }),
      resetContext: () =>
        set({
          storyboardId: null,
          storyboardTitle: "",
          effectivePresetName: null,
          effectivePresetSource: null,
          effectiveStyleProfileId: null,
          effectiveCharacterId: null,
          effectiveConfigLoaded: false,
          effectiveSdSteps: null,
          effectiveSdCfgScale: null,
          effectiveSdSamplerName: null,
          effectiveSdClipSkip: null,
        }),
    }),
    {
      name: CONTEXT_STORE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => {
        const persisted: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(state)) {
          if (typeof value === "function") continue;
          if (TRANSIENT_CONTEXT_KEYS.includes(key as keyof ContextState)) continue;
          persisted[key] = value;
        }
        return persisted as Partial<ContextState>;
      },
    }
  )
);
