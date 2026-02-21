import type { ActorGender, PromptMode } from "../../../types";
import type { WizardTag } from "./steps/AppearanceStep";
import type { WizardCategory } from "./wizardTemplates";
import { applyTagToggle, applyFreeTagToggle } from "../shared/tagUtils";

// ── Types ────────────────────────────────────────────────────

export type WizardStep = 0 | 1 | 2 | 3 | 4;

export type WizardLoRA = { loraId: number; weight: number };

export type WizardState = {
  step: WizardStep;
  // Style selection (Step 0)
  style_profile_id: number | null;
  styleBaseModel: string | null; // SD model base_model for LoRA filtering
  // Basic info (Step 1+)
  name: string;
  gender: ActorGender;
  description: string;
  templateId: string | null;
  selectedTags: WizardTag[];
  selectedLoras: WizardLoRA[];
  isSaving: boolean;
  // Prompts
  prompt_mode: PromptMode;
  custom_base_prompt: string;
  custom_negative_prompt: string;
  reference_base_prompt: string;
  reference_negative_prompt: string;
  // Preview
  previewImage: string | null; // base64
  previewSeed: number | null;
  isGenerating: boolean;
};

export type WizardAction =
  | { type: "SET_STEP"; step: WizardStep }
  | { type: "SET_STYLE_PROFILE"; id: number; baseModel: string | null }
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
  | { type: "SET_PROMPT_MODE"; mode: PromptMode }
  | { type: "SET_PROMPT_FIELD"; field: PromptField; value: string }
  | { type: "SET_GENERATING"; isGenerating: boolean }
  | { type: "SET_PREVIEW"; image: string; seed: number }
  | { type: "CLEAR_PREVIEW" };

export type PromptField =
  | "custom_base_prompt"
  | "custom_negative_prompt"
  | "reference_base_prompt"
  | "reference_negative_prompt";

// ── Reducer ──────────────────────────────────────────────────

export function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, step: action.step };
    case "SET_STYLE_PROFILE":
      return {
        ...state,
        style_profile_id: action.id,
        styleBaseModel: action.baseModel,
        // Clear incompatible LoRAs when style changes
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
      return {
        ...state,
        selectedLoras: [
          ...state.selectedLoras,
          { loraId: action.loraId, weight: action.defaultWeight },
        ],
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
    case "SET_PROMPT_MODE":
      return { ...state, prompt_mode: action.mode };
    case "SET_PROMPT_FIELD":
      return { ...state, [action.field]: action.value };
    case "SET_GENERATING":
      return { ...state, isGenerating: action.isGenerating };
    case "SET_PREVIEW":
      return {
        ...state,
        previewImage: action.image,
        previewSeed: action.seed,
        isGenerating: false,
      };
    case "CLEAR_PREVIEW":
      return { ...state, previewImage: null, previewSeed: null };
    default:
      return state;
  }
}

export const INITIAL_WIZARD_STATE: WizardState = {
  step: 0,
  style_profile_id: null,
  styleBaseModel: null,
  name: "",
  gender: "female",
  description: "",
  templateId: null,
  selectedTags: [],
  selectedLoras: [],
  isSaving: false,
  prompt_mode: "auto",
  custom_base_prompt: "",
  custom_negative_prompt: "",
  reference_base_prompt: "",
  reference_negative_prompt: "",
  previewImage: null,
  previewSeed: null,
  isGenerating: false,
};
