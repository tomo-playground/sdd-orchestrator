import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type {
  Scene,
  ActorGender,
  CastingRecommendation,
  ReferenceImage,
  ImageValidation,
  ImageGenProgress,
  StageStatus,
  StageLocationStatus,
  HiResDefaults,
  ImageDefaults,
} from "../types";
import type { GenerationDefaults } from "../hooks/usePresets";
import { DEFAULT_STRUCTURE, DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT } from "../constants";
import { generateSceneClientId } from "../utils/uuid";
import { isMultiCharStructure } from "../utils/structure";

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
  stageLocations: StageLocationStatus[];

  // Optimistic locking
  storyboardVersion: number | null;

  // Casting recommendation (Phase 20-B)
  castingRecommendation: CastingRecommendation | null;

  // Script generation in progress (blocks autoSave to prevent casting race condition)
  isScriptGenerating: boolean;

  // FastTrack skip stages (Backend SSOT, loaded from /presets)
  fastTrackSkipStages: string[];

  // Hi-Res defaults (Backend SSOT, loaded from /presets)
  hiResDefaults: HiResDefaults | null;

  // Image resolution defaults (Backend SSOT, loaded from /presets)
  imageDefaults: ImageDefaults;

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
  ipAdapterWeight: 0.35,
  ipAdapterReferenceB: "",
  ipAdapterWeightB: 0.35,
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
  stageLocations: [],
  storyboardVersion: null,
  castingRecommendation: null,
  isScriptGenerating: false,
  // Fallback — Backend SSOT: config_pipelines.FAST_TRACK_SKIP_STAGES (loaded via /presets)
  fastTrackSkipStages: ["research", "concept", "production", "explain"],
  // Backend SSOT: hi_res_defaults from /presets API (null until loaded)
  hiResDefaults: null,
  // Backend SSOT fallback: /presets API image_defaults (config.py SD_DEFAULT_WIDTH/HEIGHT)
  imageDefaults: { width: DEFAULT_IMAGE_WIDTH, height: DEFAULT_IMAGE_HEIGHT },
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
 *
 * NOTE — tts_asset_id: "transient" here means "don't trigger autoSave on update",
 * NOT "exclude from saves". The TTS Prebuild API (_update_scene_tts_asset) persists
 * tts_asset_id directly to DB, so autoSave is redundant. On explicit save,
 * buildScenesPayload(...rest) intentionally includes tts_asset_id in the payload.
 */
const SCENE_TRANSIENT_FIELDS: ReadonlySet<string> = new Set([
  "isGenerating",
  "debug_payload",
  "debug_prompt",
  "_auto_pin_previous",
  "tts_asset_id", // Backend persists directly via TTS Prebuild API; no autoSave trigger needed
]);

/** Fields excluded from persistence (transient / runtime-derived). */
const TRANSIENT_KEYS: (keyof StoryboardStore)[] = [
  "isDirty",
  "isGenerating",
  "isScriptGenerating",
  "validatingSceneId",
  "markingStatusSceneId",
  "sceneTab",
  "sceneMenuOpen",
  "advancedExpanded",
  "validationExpanded",
  "imageValidationResults",
  "imageGenProgress",
  "hiResDefaults",
  "imageDefaults",
  "loraTriggerWords",
  "characterLoras",
  "characterBLoras",
  "selectedCharacterId",
  "selectedCharacterBId",
  "selectedCharacterName",
  "selectedCharacterBName",
  "stageLocations",
];

export const useStoryboardStore = create<StoryboardStore>()(
  persist(
    (set) => ({
      ...initialState,
      isDirty: false,
      set: (updates) =>
        set((state) => {
          const merged = { ...state, ...updates };
          // Structure → Non-Dialogue 변경 시 Character B 자동 정리
          if (
            updates.structure &&
            updates.structure !== state.structure &&
            !isMultiCharStructure(updates.structure)
          ) {
            merged.selectedCharacterBId = null;
            merged.selectedCharacterBName = null;
            merged.basePromptB = "";
            merged.baseNegativePromptB = "";
            merged.characterBLoras = [];
            merged.ipAdapterReferenceB = "";
            merged.ipAdapterWeightB = 0.35;
          }
          // Character B 직접 해제 시 기존 multi 씬 scene_mode → single 전환
          if ("selectedCharacterBId" in updates && updates.selectedCharacterBId === null) {
            const hasMultiScene = state.scenes.some((s) => s.scene_mode === "multi");
            if (hasMultiScene) {
              merged.scenes = state.scenes.map((s) =>
                s.scene_mode === "multi" ? { ...s, scene_mode: "single" } : s
              );
              merged.isDirty = true;
            }
          }
          return merged;
        }),
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
          const ttsInvalidatingFields = ["script", "speaker", "voice_design_prompt"] as const;
          const existing = state.scenes.find((s) => s.client_id === clientId);
          const needsTtsReset = existing
            ? ttsInvalidatingFields.some(
                (field) =>
                  field in updates &&
                  (updates as Record<string, unknown>)[field] !==
                    (existing as Record<string, unknown>)[field]
              )
            : false;
          const finalUpdates = needsTtsReset ? { ...updates, tts_asset_id: null } : updates;
          return {
            scenes: state.scenes.map((s) =>
              s.client_id === clientId ? { ...s, ...finalUpdates } : s
            ),
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
          hiResEnabled: defaults.enable_hr,
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
