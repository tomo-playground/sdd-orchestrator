import type { StateCreator } from "zustand";
import type { ActorGender } from "../../types";

export interface PlanSlice {
  // Content
  topic: string;
  description: string;
  duration: number;
  style: string;
  language: string;
  structure: string;
  actorAGender: ActorGender;

  // Character
  selectedCharacterId: number | null;
  characterPromptMode: "auto" | "standard" | "lora";
  loraTriggerWords: string[];
  characterLoras: Array<{
    id: number;
    name: string;
    weight?: number;
    trigger_words?: string[];
    lora_type?: string;
    optimal_weight?: number;
  }>;

  // Prompt settings
  basePromptA: string;
  baseNegativePromptA: string;
  autoComposePrompt: boolean;
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

  // Setters
  setPlan: (updates: Partial<PlanSlice>) => void;
  resetPlan: () => void;
}

const initialPlanState = {
  topic: "",
  description: "",
  duration: 10,
  style: "Anime",
  language: "Korean",
  structure: "Monologue",
  actorAGender: "female" as ActorGender,
  selectedCharacterId: null,
  characterPromptMode: "auto" as const,
  loraTriggerWords: [] as string[],
  characterLoras: [] as PlanSlice["characterLoras"],
  basePromptA: "",
  baseNegativePromptA: "",
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
};

export const createPlanSlice: StateCreator<PlanSlice, [], [], PlanSlice> = (set) => ({
  ...initialPlanState,
  setPlan: (updates) => set((state) => ({ ...state, ...updates })),
  resetPlan: () => set(initialPlanState),
});

export type PlanPersistState = Omit<
  PlanSlice,
  "setPlan" | "resetPlan" | "loraTriggerWords" | "characterLoras" | "characterPromptMode"
>;

export function extractPlanPersist(state: PlanSlice): Partial<PlanPersistState> {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const {
    setPlan: _setPlan,
    resetPlan: _resetPlan,
    loraTriggerWords: _loraTriggerWords,
    characterLoras: _characterLoras,
    characterPromptMode: _characterPromptMode,
    ...rest
  } = state;
  return rest;
}
