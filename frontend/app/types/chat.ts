import type { ConceptCandidate, ProductionSnapshot, ScriptStreamEvent } from ".";
import type { ScriptProgress } from "../hooks/scriptEditor/types";

// ── Shared types ──

export type SceneEditedScene = {
  scene_index: number;
  script?: string | null;
  speaker?: string | null;
  duration?: number | null;
  image_prompt?: string | null;
  image_prompt_ko?: string | null;
};

export type SceneEditResult = {
  editedScenes: SceneEditedScene[];
  reasoning: string;
  unchangedCount: number;
};

export type AvailableOptions = {
  durations: number[];
  languages: { value: string; label: string }[];
};

export type SettingsRecommendation = {
  status: "recommend" | "clarify";
  resolved_topic?: string;
  questions?: string[];
  reasoning: string;
  duration: number;
  language: string;
  structure: string;
  available_options?: AvailableOptions;
};

// ── Discriminated Union: ChatMessage ──

type ChatMessageBase = {
  id: string;
  timestamp: number;
};

export type UserMessage = ChatMessageBase & {
  role: "user";
  contentType: "user";
  text: string;
};

export type AssistantMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "assistant";
  text: string;
};

export type SettingsRecommendMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "settings_recommend";
  text: string;
  recommendation: SettingsRecommendation;
};

export type ClarificationMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "clarification";
  text: string;
  questions?: string[];
};

export type ConceptGateMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "concept_gate";
  text: string;
  concepts: ConceptCandidate[];
  recommendedConceptId: number | null;
};

export type ReviewGateMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "review_gate";
  text: string;
  reviewResult?: Record<string, unknown>;
  productionSnapshot?: ProductionSnapshot | null;
};

export type CompletionSceneSummary = {
  order: number;
  speaker: string;
  duration: number;
  scriptPreview: string;
  emotion?: string;
};

export type CompletionMeta = {
  topic: string;
  structure: string;
  totalDuration: number;
  characterAName: string | null;
  characterBName: string | null;
  sceneSummaries: CompletionSceneSummary[];
};

export type CompletionMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "completion";
  text: string;
  meta?: CompletionMeta;
  traceUrl?: string;
};

export type ErrorMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "error";
  text: string;
  errorMessage: string;
  traceUrl?: string;
};

export type PipelineStepMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "pipeline_step";
  nodeName: string;
  nodeResult: Record<string, unknown>;
};

export type IntakeQuestion = {
  key: string;
  message: string;
  options?: { id: string; label: string; description?: string }[];
  characters?: { id: number; name: string; gender?: string; summary?: string }[];
  applicable?: boolean;
  needs_two?: boolean;
};

export type IntakeAnalysis = {
  suggested_structure: string | null;
  suggested_tone: string | null;
  reasoning: string;
};

export type IntakeGateMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "intake_gate";
  text: string;
  analysis: IntakeAnalysis;
  questions: IntakeQuestion[];
};

export type PlanReviewGateMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "plan_review_gate";
  text: string;
  topic?: string;
  directorPlan: Record<string, unknown>;
  skipStages: string[];
};

export type SceneEditDiffMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "scene_edit_diff";
  editResult: SceneEditResult;
  editApplied?: boolean;
};

export type TypingMessage = ChatMessageBase & {
  role: "assistant";
  contentType: "typing";
  text: string;
};

export type ChatMessage =
  | UserMessage
  | AssistantMessage
  | SettingsRecommendMessage
  | ClarificationMessage
  | IntakeGateMessage
  | ConceptGateMessage
  | ReviewGateMessage
  | CompletionMessage
  | ErrorMessage
  | PipelineStepMessage
  | PlanReviewGateMessage
  | SceneEditDiffMessage
  | TypingMessage;

export type ChatContentType = ChatMessage["contentType"];

export type ActiveProgress = ScriptProgress | null;

// ── SSE → Chat event mapping ──

export type NodeEventPayload = ScriptStreamEvent;
