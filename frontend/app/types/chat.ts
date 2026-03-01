import type { ConceptCandidate, ProductionSnapshot, ScriptStreamEvent } from ".";
import type { SceneItem, ScriptProgress } from "../hooks/scriptEditor/types";

// ── Message content types ──

export type ChatContentType =
  | "user"
  | "assistant"
  | "settings_recommend"
  | "clarification"
  | "concept_gate"
  | "review_gate"
  | "completion"
  | "error"
  | "pipeline_step"
  | "plan_review_gate"
  | "scene_edit_diff";

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

export type SettingsRecommendation = {
  status: "recommend" | "clarify";
  resolved_topic?: string; // Backend이 대화에서 추론한 최종 토픽
  questions?: string[];
  reasoning: string;
  duration: number;
  language: string;
  structure: string;
  character_id: number | null;
  character_name: string | null;
  character_b_id: number | null;
  character_b_name: string | null;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  contentType: ChatContentType;
  text?: string;
  timestamp: number;
  // Typed payloads per contentType
  recommendation?: SettingsRecommendation;
  concepts?: ConceptCandidate[];
  recommendedConceptId?: number | null;
  scenes?: SceneItem[];
  reviewResult?: Record<string, unknown>;
  productionSnapshot?: ProductionSnapshot | null;
  errorMessage?: string;
  questions?: string[];
  nodeName?: string;
  nodeResult?: Record<string, unknown>;
  directorPlan?: Record<string, unknown>;
  skipStages?: string[];
  editResult?: SceneEditResult;
  editApplied?: boolean;
};

export type ActiveProgress = ScriptProgress | null;

// ── SSE → Chat event mapping ──

export type NodeEventPayload = ScriptStreamEvent;
