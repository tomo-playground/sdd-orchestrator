import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type {
  Scene,
  ActorGender,
  ReferenceImage,
  ImageValidation,
  ImageGenProgress,
  StageStatus,
} from "../types";
import type { GenerationDefaults } from "../hooks/usePresets";
import { DEFAULT_STRUCTURE } from "../constants";
import { generateSceneClientId } from "../utils/uuid";

type LoraEntry = {
  id: number;
  name: string;
  weight?: number;
  trigger_words?: string[];
  lora_type?: string;
  optimal_weight?: number;
};

export interface StoryboardStore {
  // Content plan
  topic: string;
  description: string;
  duration: number;
  style: string;
  language: string;
  structure: string;
  actorAGender: ActorGender;

  // Character A
  selectedCharacterId: number | null;
  selectedCharacterName: string | null;
  loraTriggerWords: string[];
  characterLoras: LoraEntry[];

  // Character B
  selectedCharacterBId: number | null;
  selectedCharacterBName: string | null;
  characterBLoras: LoraEntry[];
  basePromptB: string;
  baseNegativePromptB: string;

  // Prompt settings
  basePromptA: string;
  baseNegativePromptA: string;
  autoRewritePrompt: boolean;
  autoReplaceRiskyTags: boolean;
  hiResEnabled: boolean;
  veoEnabled: boolean;

  // ControlNet / IP-Adapter
  useControlnet: boolean;
  controlnetWeight: number;
  useIpAdapter: boolean;
  ipAdapterReference: string;
  ipAdapterWeight: number;
  ipAdapterReferenceB: string;
  ipAdapterWeightB: number;

  // Scenes
  scenes: Scene[];
  currentSceneIndex: number;
  isGenerating: boolean;
  multiGenEnabled: boolean;
  referenceImages: ReferenceImage[];
  imageValidationResults: Record<string, ImageValidation>;
  validatingSceneId: string | null;
  markingStatusSceneId: string | null;
  sceneTab: Record<string, "validate" | "debug" | null>;
  sceneMenuOpen: string | null;
  advancedExpanded: Record<string, boolean>;
  validationExpanded: Record<string, boolean>;

  // Image generation progress (SSE)
  imageGenProgress: Record<string, ImageGenProgress>;

  // Stage workflow
  stageStatus: StageStatus;

  // Optimistic locking
  storyboardVersion: number | null;

  // Dirty flag
  isDirty: boolean;

  // Setters
  set: (updates: Partial<StoryboardStore>) => void;
  setScenes: (scenes: Scene[]) => void;
  updateScene: (clientId: string, updates: Partial<Scene>) => void;
  removeScene: (clientId: string) => void;
  reorderScenes: (fromIndex: number, toIndex: number) => void;
  applyGenerationDefaults: (defaults: GenerationDefaults) => void;
  reset: () => void;
}

const initialState: Omit<
  StoryboardStore,
  | "set"
  | "setScenes"
  | "updateScene"
  | "removeScene"
  | "reorderScenes"
  | "applyGenerationDefaults"
  | "reset"
  | "isDirty"
> = {
  // Content plan fields
  topic: "",
  description: "",
  duration: 30,
  style: "Anime",
  language: "Korean",
  structure: DEFAULT_STRUCTURE,
  actorAGender: "female" as ActorGender,
  // Image plan fields
  selectedCharacterId: null,
  selectedCharacterName: null,
  selectedCharacterBId: null,
  selectedCharacterBName: null,
  loraTriggerWords: [],
  characterLoras: [],
  characterBLoras: [],
  basePromptA: "",
  baseNegativePromptA: "",
  basePromptB: "",
  baseNegativePromptB: "",
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
  imageValidationResults: {},
  validatingSceneId: null,
  markingStatusSceneId: null,
  sceneTab: {},
  sceneMenuOpen: null,
  advancedExpanded: {},
  validationExpanded: {},
  imageGenProgress: {},
  stageStatus: "pending" as StageStatus,
  storyboardVersion: null,
};

export const STORYBOARD_STORE_KEY = "shorts-producer:storyboard:v1";

// Pre-hydration cleanup: clear localStorage before Zustand hydrates old data
if (typeof window !== "undefined") {
  const params = new URLSearchParams(window.location.search);
  if (params.get("new") === "true") {
    localStorage.removeItem(STORYBOARD_STORE_KEY);
  }
}

/**
 * Scene fields that are transient (UI-only) and should NOT trigger isDirty / autoSave.
 * e.g. isGenerating is purely visual state — persisting it would cause race conditions
 * where autoSave sends stale image_asset_id: null while generation is in progress.
 */
const SCENE_TRANSIENT_FIELDS: ReadonlySet<string> = new Set([
  "isGenerating",
  "debug_payload",
  "debug_prompt",
  "_auto_pin_previous",
]);

/** Fields excluded from persistence (transient / runtime-derived). */
const TRANSIENT_KEYS: (keyof StoryboardStore)[] = [
  "isDirty",
  "isGenerating",
  "validatingSceneId",
  "markingStatusSceneId",
  "sceneTab",
  "sceneMenuOpen",
  "advancedExpanded",
  "validationExpanded",
  "imageValidationResults",
  "imageGenProgress",
  "loraTriggerWords",
  "characterLoras",
];

export const useStoryboardStore = create<StoryboardStore>()(
  persist(
    (set) => ({
      ...initialState,
      isDirty: false,
      set: (updates) => set((state) => ({ ...state, ...updates })),
      setScenes: (scenes) =>
        set((state) => ({
          scenes,
          isDirty: true,
          currentSceneIndex: Math.min(state.currentSceneIndex, Math.max(0, scenes.length - 1)),
        })),
      updateScene: (clientId, updates) =>
        set((state) => {
          const hasPersistableChange = Object.keys(updates).some(
            (key) => !SCENE_TRANSIENT_FIELDS.has(key)
          );
          return {
            scenes: state.scenes.map((s) => (s.client_id === clientId ? { ...s, ...updates } : s)),
            ...(hasPersistableChange && { isDirty: true }),
          };
        }),
      removeScene: (clientId) =>
        set((state) => {
          const newScenes = state.scenes.filter((s) => s.client_id !== clientId);
          return {
            scenes: newScenes,
            isDirty: true,
            currentSceneIndex: Math.min(state.currentSceneIndex, Math.max(0, newScenes.length - 1)),
          };
        }),
      reorderScenes: (fromIndex, toIndex) =>
        set((state) => {
          if (fromIndex < 0 || fromIndex >= state.scenes.length) return state;
          if (toIndex < 0 || toIndex >= state.scenes.length) return state;
          if (fromIndex === toIndex) return state;
          const scenes = [...state.scenes];
          const [moved] = scenes.splice(fromIndex, 1);
          scenes.splice(toIndex, 0, moved);
          const reordered = scenes.map((s, i) => ({ ...s, order: i }));
          const selectedCid = state.scenes[state.currentSceneIndex]?.client_id;
          const newIndex = reordered.findIndex((s) => s.client_id === selectedCid);
          return {
            scenes: reordered,
            currentSceneIndex: Math.max(0, newIndex),
            isDirty: true,
          };
        }),
      applyGenerationDefaults: (defaults: GenerationDefaults) =>
        set(() => ({
          useControlnet: defaults.use_controlnet,
          controlnetWeight: defaults.controlnet_weight,
          useIpAdapter: defaults.use_ip_adapter,
          ipAdapterWeight: defaults.ip_adapter_weight,
          multiGenEnabled: defaults.multi_gen_enabled,
        })),
      reset: () => set({ ...initialState, isDirty: false }),
    }),
    {
      name: STORYBOARD_STORE_KEY,
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
      onRehydrateStorage: () => (state) => {
        if (state?.scenes) {
          const needsMigration = state.scenes.some((s) => !s.client_id);
          if (needsMigration) {
            state.scenes = state.scenes.map((s) =>
              s.client_id ? s : { ...s, client_id: generateSceneClientId() }
            );
          }
        }
      },
    }
  )
);
