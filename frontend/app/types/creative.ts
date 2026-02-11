// Shared types for the Creative Lab feature

export type CreativeSession = {
  id: number;
  objective: string;
  evaluation_criteria: Record<string, unknown> | null;
  character_id: number | null;
  context: Record<string, unknown> | null;
  agent_config: Array<Record<string, unknown>> | null;
  final_output: Record<string, unknown> | null;
  max_rounds: number;
  total_token_usage: Record<string, unknown> | null;
  status: string;
  session_type: string;
  director_mode: "auto" | "advisor";
  concept_candidates: ConceptCandidates | null;
  selected_concept_index: number | null;
  created_at: string | null;
};

export type CreativeRound = {
  id: number;
  session_id: number;
  round_number: number;
  leader_summary: string | null;
  round_decision: string | null;
  best_agent_role: string | null;
  best_score: number | null;
  leader_direction: string | null;
  created_at: string | null;
};

export type CreativeTrace = {
  id: number;
  session_id: number;
  round_number: number;
  sequence: number;
  trace_type: string;
  agent_role: string;
  agent_preset_id: number | null;
  input_prompt: string;
  output_content: string;
  score: number | null;
  feedback: string | null;
  model_id: string;
  token_usage: Record<string, number> | null;
  latency_ms: number;
  temperature: number;
  parent_trace_id: number | null;
  diff_summary: string | null;
  // V2 fields
  phase: string | null;
  step_name: string | null;
  target_agent: string | null;
  decision_context: DecisionContext | null;
  retry_count: number;
  created_at: string | null;
};

export type CreativeTimeline = {
  session: CreativeSession;
  rounds: CreativeRound[];
  traces: CreativeTrace[];
};

export type SessionListResponse = {
  items: CreativeSession[];
  total: number;
};

// V2 types

export type ConceptCandidate = {
  agent_role: string;
  concept: ConceptData;
  score: number;
  feedback: string;
  breakdown?: Record<string, number>;
};

export type ConceptData = {
  title: string;
  hook: string;
  hook_strength?: string;
  arc: string;
  key_moments?: KeyMoment[];
  mood_progression?: string;
  estimated_scenes?: number;
  pacing_note?: string;
};

export type KeyMoment = {
  beat: string;
  description: string;
  camera_hint?: string;
};

export type ConceptCandidates = {
  candidates: ConceptCandidate[];
  evaluation_summary: string;
};

export type DecisionContext = {
  mode: "auto" | "advisor";
  options: DecisionOption[];
  selected: string | null;
  reason: string;
  confidence: number;
  escalated_to_user: boolean;
};

export type DecisionOption = {
  label: string;
  score: number;
  pros: string[];
  cons: string[];
};

export type StepProgress = {
  status: "pending" | "running" | "done" | "failed" | "review" | "skipped";
  retry_count?: number;
  started_at?: string;
};

export type PipelineProgress = {
  scriptwriter?: StepProgress | string;
  cinematographer?: StepProgress | string;
  sound_designer?: StepProgress | string;
  copyright_reviewer?: StepProgress | string;
};

export type PipelineStatusResponse = {
  status: string;
  session_type: string;
  progress?: PipelineProgress;
  concept_candidates?: ConceptCandidates;
  selected_concept_index?: number;
};

export type ShortsSessionCreate = {
  topic: string;
  duration: number;
  structure: string;
  language: string;
  character_id?: number;
  character_ids?: Record<string, number>; // {"A": 1, "B": 2}
  director_mode: string;
  max_rounds: number;
  references?: string[];
  disabled_steps?: string[];
};

export type SendToStudioRequest = {
  group_id: number;
  title?: string;
  deep_parse?: boolean;
};

export type CopyrightCheck = {
  type: string;
  status: "PASS" | "WARN" | "FAIL";
  detail: string | null;
  suggestion?: string;
};

export type CopyrightResult = {
  overall: "PASS" | "WARN" | "FAIL";
  checks: CopyrightCheck[];
  confidence: number;
};

export type MusicRecommendation = {
  prompt: string;
  mood: string;
  duration: number;
  reasoning: string;
};

// ── Interactive Review ────────────────────────────────────

export type QCIssue = {
  severity: "critical" | "warning" | "suggestion";
  category: "readability" | "hook" | "emotion" | "tts" | "diversity" | "consistency";
  scene: number;
  description: string;
};

export type QCAnalysis = {
  overall_rating: "good" | "needs_revision" | "poor";
  score: number;
  score_breakdown: Record<string, number>;
  summary: string;
  issues: QCIssue[];
  strengths: string[];
  revision_suggestions: string[];
};

export type ReviewMessage = {
  role: "system" | "user" | "agent";
  content: string;
  timestamp: string;
};

export type StepReview = {
  step: string;
  result: Record<string, unknown> | null;
  qc_analysis: QCAnalysis | null;
  messages: ReviewMessage[];
};

export type ReviewActionRequest = {
  action: "approve" | "revise";
  feedback?: string;
};

export type PipelineLog = {
  ts: string;
  step: string;
  msg: string;
  level: string;
};

export type CreativeSceneSummary = {
  order: number;
  script: string;
  speaker: string;
  duration: number;
  camera?: string;
  environment?: string;
  image_prompt?: string; // SD prompt (English) - not displayed in summary table
  image_prompt_ko?: string; // Scene description (Korean) - displayed in summary
};
