import type {
  ConceptCandidate,
  FeedbackPreset,
  PipelineStep,
  ProductionSnapshot,
  Scene,
} from "../../types";

export type SceneItem = {
  id: number;
  client_id: string;
  order: number;
  script: string;
  speaker: string;
  duration: number;
  image_prompt: string;
  image_prompt_ko: string;
  image_url: string | null;
  context_tags?: Record<string, string | string[]>;
  character_actions?: Scene["character_actions"];
  use_controlnet?: boolean | null;
  controlnet_weight?: number | null;
  controlnet_pose?: string | null;
  use_ip_adapter?: boolean | null;
  ip_adapter_weight?: number | null;
  multi_gen_enabled?: boolean | null;
  negative_prompt_extra?: string | null;
  voice_design_prompt?: string | null;
  head_padding?: number | null;
  tail_padding?: number | null;
  ken_burns_preset?: string | null;
  background_id?: number | null;
};

export type ScriptProgress = {
  node: string;
  label: string;
  percent: number;
};

export type ScriptEditorState = {
  topic: string;
  description: string;
  duration: number;
  language: string;
  structure: string;
  characterId: number | null;
  characterName: string | null;
  characterBId: number | null;
  characterBName: string | null;
  scenes: SceneItem[];
  isGenerating: boolean;
  progress: ScriptProgress | null;
  storyboardId: number | null;
  storyboardVersion: number | null;
  isSaving: boolean;
  directorSkipStages: string[];
  threadId: string | null;
  isWaitingForInput: boolean;
  isWaitingForConcept: boolean;
  concepts: ConceptCandidate[] | null;
  recommendedConceptId: number | null;
  feedbackSubmitted: boolean;
  justGenerated: boolean;
  references: string;
  feedbackPresets: FeedbackPreset[] | null;
  pipelineSteps: PipelineStep[];
  nodeResults: Record<string, Record<string, unknown>>;
  traceId: string | null;
  productionSnapshot: ProductionSnapshot | null;
  interactionMode: "auto" | "guided" | "hands_on";
  isWaitingForPlan: boolean;
  chatContext: Array<{ role: string; text: string }>;
};

export type ResumeOptions = {
  feedbackPreset?: string;
  feedbackPresetParams?: Record<string, string>;
  customConcept?: { title: string; concept: string };
};

export type ResumeAction =
  | "approve"
  | "revise"
  | "select"
  | "regenerate"
  | "custom_concept"
  | "proceed"
  | "revise_plan";

export type ScriptEditorActions = ScriptEditorState & {
  setField: <K extends keyof ScriptEditorState>(key: K, value: ScriptEditorState[K]) => void;
  updateScene: (index: number, patch: Partial<SceneItem>) => void;
  generate: () => Promise<void>;
  resume: (
    action: ResumeAction,
    feedback?: string,
    conceptId?: number,
    options?: ResumeOptions
  ) => Promise<void>;
  submitFeedback: (rating: "positive" | "negative", feedbackText?: string) => Promise<void>;
  save: () => Promise<void>;
  loadStoryboard: (id: number) => Promise<void>;
  reset: () => void;
  /** SSE 파이프라인 스트림을 중단하고 isGenerating을 리셋한다. */
  cancel: () => void;
};

export type ScriptEditorOptions = {
  onSaved?: (id: number) => void;
  /** SSE event callback — injected into processSSEStream for chat UI. */
  onNodeEvent?: (event: import("../../types").ScriptStreamEvent) => void;
};
