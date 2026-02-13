import type { ActorGender } from "../../../types";
import type { WizardTag } from "./steps/AppearanceStep";
import type { WizardCategory } from "./wizardTemplates";

// ── Types ────────────────────────────────────────────────────

export type WizardStep = 1 | 2 | 3;

export type WizardLoRA = { loraId: number; weight: number };

export type WizardState = {
  step: WizardStep;
  name: string;
  gender: ActorGender;
  description: string;
  templateId: string | null;
  selectedTags: WizardTag[];
  selectedLoras: WizardLoRA[];
  isSaving: boolean;
  // Preview
  previewImage: string | null; // base64
  previewSeed: number | null;
  isGenerating: boolean;
};

export type WizardAction =
  | { type: "SET_STEP"; step: WizardStep }
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
  | { type: "SET_GENERATING"; isGenerating: boolean }
  | { type: "SET_PREVIEW"; image: string; seed: number }
  | { type: "CLEAR_PREVIEW" };

// ── Reducer ──────────────────────────────────────────────────

export function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, step: action.step };
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
    case "TOGGLE_TAG": {
      const { tag, category } = action;
      const exists = state.selectedTags.some((t) => t.tagId === tag.tagId);
      if (exists) {
        return { ...state, selectedTags: state.selectedTags.filter((t) => t.tagId !== tag.tagId) };
      }
      if (category.selectMode === "single") {
        const filtered = state.selectedTags.filter((t) => t.groupName !== category.groupName);
        return { ...state, selectedTags: [...filtered, tag] };
      }
      if (category.maxSelect) {
        const groupCount = state.selectedTags.filter(
          (t) => t.groupName === category.groupName
        ).length;
        if (groupCount >= category.maxSelect) return state;
      }
      return { ...state, selectedTags: [...state.selectedTags, tag] };
    }
    case "ADD_TAG": {
      const exists = state.selectedTags.some((t) => t.tagId === action.tag.tagId);
      if (exists) {
        return {
          ...state,
          selectedTags: state.selectedTags.filter((t) => t.tagId !== action.tag.tagId),
        };
      }
      return { ...state, selectedTags: [...state.selectedTags, action.tag] };
    }
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
    case "SET_GENERATING":
      return { ...state, isGenerating: action.isGenerating };
    case "SET_PREVIEW":
      return { ...state, previewImage: action.image, previewSeed: action.seed, isGenerating: false };
    case "CLEAR_PREVIEW":
      return { ...state, previewImage: null, previewSeed: null };
    default:
      return state;
  }
}

export const INITIAL_WIZARD_STATE: WizardState = {
  step: 1,
  name: "",
  gender: "female",
  description: "",
  templateId: null,
  selectedTags: [],
  selectedLoras: [],
  isSaving: false,
  previewImage: null,
  previewSeed: null,
  isGenerating: false,
};
