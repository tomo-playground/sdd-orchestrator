// Shared types for the Creative Lab feature

export type CreativeSession = {
  id: number;
  task_type: string;
  objective: string;
  evaluation_criteria: Record<string, unknown> | null;
  character_id: number | null;
  context: Record<string, unknown> | null;
  agent_config: Array<Record<string, unknown>> | null;
  final_output: Record<string, unknown> | null;
  max_rounds: number;
  total_token_usage: Record<string, unknown> | null;
  status: string;
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

export type SendToStudioResponse = {
  storyboard_id: number;
  scenes_created: number;
};
