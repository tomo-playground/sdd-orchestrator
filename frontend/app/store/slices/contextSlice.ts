import type { StateCreator } from "zustand";
import type { ProjectItem, GroupItem } from "../../types";

export interface ContextSlice {
  projects: ProjectItem[];
  groups: GroupItem[];
  isLoadingProjects: boolean;
  isLoadingGroups: boolean;
  effectivePresetName: string | null;
  effectivePresetSource: string | null;
  effectiveStyleProfileId: number | null;
  effectiveCharacterId: number | null;
  effectiveConfigLoaded: boolean;
  effectiveSdSteps: number | null;
  effectiveSdCfgScale: number | null;
  effectiveSdSamplerName: string | null;
  effectiveSdClipSkip: number | null;

  setProjects: (projects: ProjectItem[]) => void;
  setGroups: (groups: GroupItem[]) => void;
  setContextLoading: (updates: Partial<Pick<ContextSlice, "isLoadingProjects" | "isLoadingGroups">>) => void;
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

const initialContextState = {
  projects: [] as ProjectItem[],
  groups: [] as GroupItem[],
  isLoadingProjects: false,
  isLoadingGroups: false,
  effectivePresetName: null as string | null,
  effectivePresetSource: null as string | null,
  effectiveStyleProfileId: null as number | null,
  effectiveCharacterId: null as number | null,
  effectiveConfigLoaded: false,
  effectiveSdSteps: null as number | null,
  effectiveSdCfgScale: null as number | null,
  effectiveSdSamplerName: null as string | null,
  effectiveSdClipSkip: null as number | null,
};

export const createContextSlice: StateCreator<ContextSlice, [], [], ContextSlice> = (set) => ({
  ...initialContextState,
  setProjects: (projects) => set({ projects }),
  setGroups: (groups) => set({ groups }),
  setContextLoading: (updates) => set((state) => ({ ...state, ...updates })),
  setEffectivePreset: (name, source) => set({ effectivePresetName: name, effectivePresetSource: source }),
  setEffectiveDefaults: (styleId, charId, loaded) => set({
    effectiveStyleProfileId: styleId,
    effectiveCharacterId: charId,
    effectiveConfigLoaded: loaded,
  }),
  setEffectiveSdParams: (params) => set({
    effectiveSdSteps: params.steps,
    effectiveSdCfgScale: params.cfgScale,
    effectiveSdSamplerName: params.samplerName,
    effectiveSdClipSkip: params.clipSkip,
  }),
  resetContext: () => set(initialContextState),
});
