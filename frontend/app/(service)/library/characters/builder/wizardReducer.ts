import type { ActorGender } from "../../../../types";
import type { WizardTag } from "./steps/AppearanceStep";
import type { WizardCategory } from "./wizardTemplates";
import { applyTagToggle, applyFreeTagToggle } from "../shared/tagUtils";

// ── Types ────────────────────────────────────────────────────

export type WizardStep = 0 | 1 | 2 | 3 | 4;

export type WizardLoRA = { loraId: number; weight: number };

export type CandidateImage = { image: string; seed: number };

export type WizardState = {
  step: WizardStep;
  // Group selection (Step 0)
  group_id: number | null;
  groupStyleProfileId: number | null; // derived from selected group
  styleBaseModel: string | null; // SD model base_model for LoRA filtering
  styleLoraIds: number[]; // LoRA IDs from StyleProfile (excluded from selection)
  // Basic info (Step 1+)
  name: string;
  gender: ActorGender;
  description: string;
  templateId: string | null;
  selectedTags: WizardTag[];
  selectedLoras: WizardLoRA[];
  isSaving: boolean;
  // Prompts
  scene_positive_prompt: string;
  scene_negative_prompt: string;
  reference_positive_prompt: string;
  reference_negative_prompt: string;
  // Preview
  previewImage: string | null; // base64
  previewSeed: number | null;
  previewCandidates: CandidateImage[];
  selectedCandidateIndex: number;
  isGenerating: boolean;
};

export type WizardAction =
  | { type: "SET_STEP"; step: WizardStep }
  | {
      type: "SET_GROUP";
      groupId: number;
      styleProfileId: number | null;
      baseModel: string | null;
      styleLoraIds: number[];
    }
  | { type: "SET_NAME"; name: string }
  | { type: "SET_GENDER"; gender: ActorGender }
  | { type: "SET_DESCRIPTION"; description: string }
  | { type: "SELECT_TEMPLATE"; templateId: string; tags: WizardTag[]; gender: ActorGender }
  | { type: "TOGGLE_TAG"; tag: WizardTag; category: WizardCategory }
  | { type: "ADD_TAG"; tag: WizardTag }
  | { type: "SET_SAVING"; isSaving: boolean }
  | { type: "TOGGLE_LORA"; loraId: number; defaultWeight: number }
  | { type: "UPDATE_LORA_WEIGHT"; loraId: number; weight: number }
  | { type: "CLEAR_LORAS" }
  | { type: "SET_PROMPT_FIELD"; field: PromptField; value: string }
  | { type: "SET_GENERATING"; isGenerating: boolean }
  | { type: "SET_PREVIEW"; image: string; seed: number; candidates: CandidateImage[] }
  | { type: "SELECT_CANDIDATE"; index: number }
  | { type: "CLEAR_PREVIEW" };

export type PromptField =
  | "scene_positive_prompt"
  | "scene_negative_prompt"
  | "reference_positive_prompt"
  | "reference_negative_prompt";

// ── Reducer ──────────────────────────────────────────────────

export function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, step: action.step };
    case "SET_GROUP":
      return {
        ...state,
        group_id: action.groupId,
        groupStyleProfileId: action.styleProfileId,
        styleBaseModel: action.baseModel,
        styleLoraIds: action.styleLoraIds,
        // Clear incompatible LoRAs when group/style changes
        selectedLoras: [],
      };
    case "SET_NAME":
      return { ...state, name: action.name };
    case "SET_GENDER":
      return { ...state, gender: action.gender };
    case "SET_DESCRIPTION":
      return { ...state, description: action.description };
    case "SELECT_TEMPLATE":
      return {
        ...state,
        templateId: action.templateId,
        selectedTags: action.tags,
        gender: action.gender,
      };
    case "TOGGLE_TAG":
      return {
        ...state,
        selectedTags: applyTagToggle(state.selectedTags, action.tag, action.category),
      };
    case "ADD_TAG":
      return { ...state, selectedTags: applyFreeTagToggle(state.selectedTags, action.tag) };
    case "SET_SAVING":
      return { ...state, isSaving: action.isSaving };
    case "TOGGLE_LORA": {
      const exists = state.selectedLoras.some((l) => l.loraId === action.loraId);
      if (exists) {
        return {
          ...state,
          selectedLoras: state.selectedLoras.filter((l) => l.loraId !== action.loraId),
        };
      }
      // Single-select: replace previous character LoRA
      return {
        ...state,
        selectedLoras: [{ loraId: action.loraId, weight: action.defaultWeight }],
      };
    }
    case "UPDATE_LORA_WEIGHT":
      return {
        ...state,
        selectedLoras: state.selectedLoras.map((l) =>
          l.loraId === action.loraId ? { ...l, weight: action.weight } : l
        ),
      };
    case "CLEAR_LORAS":
      return { ...state, selectedLoras: [] };
    case "SET_PROMPT_FIELD":
      return { ...state, [action.field]: action.value };
    case "SET_GENERATING":
      return { ...state, isGenerating: action.isGenerating };
    case "SET_PREVIEW":
      return {
        ...state,
        previewImage: action.image,
        previewSeed: action.seed,
        previewCandidates: action.candidates,
        selectedCandidateIndex: 0,
        isGenerating: false,
      };
    case "SELECT_CANDIDATE": {
      const c = state.previewCandidates[action.index];
      if (!c) return state;
      return {
        ...state,
        previewImage: c.image,
        previewSeed: c.seed,
        selectedCandidateIndex: action.index,
      };
    }
    case "CLEAR_PREVIEW":
      return {
        ...state,
        previewImage: null,
        previewSeed: null,
        previewCandidates: [],
        selectedCandidateIndex: 0,
      };
    default:
      return state;
  }
}

export const INITIAL_WIZARD_STATE: WizardState = {
  step: 0,
  group_id: null,
  groupStyleProfileId: null,
  styleBaseModel: null,
  styleLoraIds: [],
  name: "",
  gender: "female",
  description: "",
  templateId: null,
  selectedTags: [],
  selectedLoras: [],
  isSaving: false,
  scene_positive_prompt: "",
  scene_negative_prompt: "",
  reference_positive_prompt: "",
  reference_negative_prompt: "",
  previewImage: null,
  previewSeed: null,
  previewCandidates: [],
  selectedCandidateIndex: 0,
  isGenerating: false,
};
