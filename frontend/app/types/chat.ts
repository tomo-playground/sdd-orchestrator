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
  | "plan_review_gate";

export type SettingsRecommendation = {
  status: "recommend" | "clarify";
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
};

export type ActiveProgress = ScriptProgress | null;

// ── SSE → Chat event mapping ──

export type NodeEventPayload = ScriptStreamEvent;
