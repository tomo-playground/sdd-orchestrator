import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { Scene, SceneValidation, ImageValidation, ReferenceImage } from "../types";
import type { PlanSlice } from "./slices/planSlice";
import type { ScenesSlice } from "./slices/scenesSlice";

/** Image-related fields extracted from PlanSlice. */
type ImagePlanFields = Pick<
  PlanSlice,
  | "selectedCharacterId"
  | "selectedCharacterName"
  | "selectedCharacterBId"
  | "selectedCharacterBName"
  | "characterPromptMode"
  | "loraTriggerWords"
  | "characterLoras"
  | "characterBLoras"
  | "basePromptA"
  | "baseNegativePromptA"
  | "basePromptB"
  | "baseNegativePromptB"
  | "autoComposePrompt"
  | "autoRewritePrompt"
  | "autoReplaceRiskyTags"
  | "hiResEnabled"
  | "veoEnabled"
  | "useControlnet"
  | "controlnetWeight"
  | "useIpAdapter"
  | "ipAdapterReference"
  | "ipAdapterWeight"
  | "ipAdapterReferenceB"
  | "ipAdapterWeightB"
>;

/** Scene data fields (without slice setters). */
type SceneDataFields = Omit<
  ScenesSlice,
  "setScenes" | "updateScene" | "removeScene" | "setCurrentSceneIndex" | "setScenesState" | "resetScenes"
>;

export interface StoryboardStore extends ImagePlanFields, SceneDataFields {
  storyboardId: number | null;
  storyboardTitle: string;

  // Setters
  set: (updates: Partial<StoryboardStore>) => void;
  setScenes: (scenes: Scene[]) => void;
  updateScene: (sceneId: number, updates: Partial<Scene>) => void;
  removeScene: (sceneId: number) => void;
  reset: () => void;
}

const initialState: Omit<StoryboardStore, "set" | "setScenes" | "updateScene" | "removeScene" | "reset"> = {
  storyboardId: null,
  storyboardTitle: "",
  // Image plan fields
  selectedCharacterId: null,
  selectedCharacterName: null,
  selectedCharacterBId: null,
  selectedCharacterBName: null,
  characterPromptMode: "auto",
  loraTriggerWords: [],
  characterLoras: [],
  characterBLoras: [],
  basePromptA: "",
  baseNegativePromptA: "",
  basePromptB: "",
  baseNegativePromptB: "",
  autoComposePrompt: true,
  autoRewritePrompt: true,
  autoReplaceRiskyTags: false,
  hiResEnabled: false,
  veoEnabled: false,
  useControlnet: true,
  controlnetWeight: 0.8,
  useIpAdapter: false,
  ipAdapterReference: "",
  ipAdapterWeight: 0.7,
  ipAdapterReferenceB: "",
  ipAdapterWeightB: 0.7,
  // Scenes
  scenes: [],
  currentSceneIndex: 0,
  isGenerating: false,
  multiGenEnabled: false,
  referenceImages: [],
  validationResults: {},
  validationSummary: { ok: 0, warn: 0, error: 0 },
  imageValidationResults: {},
  validatingSceneId: null,
  markingStatusSceneId: null,
  sceneTab: {},
  sceneMenuOpen: null,
  advancedExpanded: {},
  suggestionExpanded: {},
  validationExpanded: {},
};

const STORE_KEY = "shorts-producer:storyboard:v1";

/** Fields excluded from persistence (transient / runtime-derived). */
const TRANSIENT_KEYS: (keyof StoryboardStore)[] = [
  "isGenerating",
  "validatingSceneId",
  "markingStatusSceneId",
  "sceneTab",
  "sceneMenuOpen",
  "advancedExpanded",
  "suggestionExpanded",
  "validationExpanded",
  "validationResults",
  "validationSummary",
  "imageValidationResults",
  "loraTriggerWords",
  "characterLoras",
  "characterPromptMode",
];

export const useStoryboardStore = create<StoryboardStore>()(
  persist(
    (set) => ({
      ...initialState,
      set: (updates) => set((state) => ({ ...state, ...updates })),
      setScenes: (scenes) =>
        set((state) => ({
          scenes,
          currentSceneIndex: Math.min(state.currentSceneIndex, Math.max(0, scenes.length - 1)),
        })),
      updateScene: (sceneId, updates) =>
        set((state) => ({
          scenes: state.scenes.map((s) => (s.id === sceneId ? { ...s, ...updates } : s)),
        })),
      removeScene: (sceneId) =>
        set((state) => {
          const newScenes = state.scenes.filter((s) => s.id !== sceneId);
          return {
            scenes: newScenes,
            currentSceneIndex: Math.min(state.currentSceneIndex, Math.max(0, newScenes.length - 1)),
          };
        }),
      reset: () => set(initialState),
    }),
    {
      name: STORE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => {
        const persisted: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(state)) {
          if (typeof value === "function") continue;
          if (TRANSIENT_KEYS.includes(key as keyof StoryboardStore)) continue;
          persisted[key] = value;
        }
        return persisted as Partial<StoryboardStore>;
      },
    },
  ),
);
