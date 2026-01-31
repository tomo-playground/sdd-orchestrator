import type { StateCreator } from "zustand";
import type { Scene, SceneValidation, ImageValidation, ReferenceImage } from "../../types";

export interface ScenesSlice {
  scenes: Scene[];
  currentSceneIndex: number;
  isGenerating: boolean;
  multiGenEnabled: boolean;

  // IP-Adapter reference images
  referenceImages: ReferenceImage[];

  // Validation
  validationResults: Record<number, SceneValidation>;
  validationSummary: { ok: number; warn: number; error: number };
  imageValidationResults: Record<number, ImageValidation>;
  validatingSceneId: number | null;
  markingStatusSceneId: number | null;

  // Scene UI state
  sceneTab: Record<number, "validate" | "debug" | null>;
  sceneMenuOpen: number | null;
  advancedExpanded: Record<number, boolean>;
  suggestionExpanded: Record<number, boolean>;
  validationExpanded: Record<number, boolean>;

  // Setters
  setScenes: (scenes: Scene[]) => void;
  updateScene: (sceneId: number, updates: Partial<Scene>) => void;
  removeScene: (sceneId: number) => void;
  setCurrentSceneIndex: (index: number) => void;
  setScenesState: (updates: Partial<ScenesSlice>) => void;
  resetScenes: () => void;
}

const initialScenesState = {
  scenes: [] as Scene[],
  currentSceneIndex: 0,
  isGenerating: false,
  multiGenEnabled: false,
  referenceImages: [] as ReferenceImage[],
  validationResults: {} as Record<number, SceneValidation>,
  validationSummary: { ok: 0, warn: 0, error: 0 },
  imageValidationResults: {} as Record<number, ImageValidation>,
  validatingSceneId: null,
  markingStatusSceneId: null,
  sceneTab: {} as Record<number, "validate" | "debug" | null>,
  sceneMenuOpen: null,
  advancedExpanded: {} as Record<number, boolean>,
  suggestionExpanded: {} as Record<number, boolean>,
  validationExpanded: {} as Record<number, boolean>,
};

export const createScenesSlice: StateCreator<ScenesSlice, [], [], ScenesSlice> = (set) => ({
  ...initialScenesState,
  setScenes: (scenes) => set({ scenes, currentSceneIndex: 0 }),
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
  setCurrentSceneIndex: (index) => set({ currentSceneIndex: index }),
  setScenesState: (updates) => set((state) => ({ ...state, ...updates })),
  resetScenes: () => set(initialScenesState),
});
