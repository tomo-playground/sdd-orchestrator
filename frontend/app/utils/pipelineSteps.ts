import type { PipelineStep, ScriptStreamEvent } from "../types";

/** Express 프리셋 기본 skip_stages (Backend SSOT: config_pipelines.py VALID_SKIP_STAGES) */
export const EXPRESS_SKIP_STAGES = ["research", "concept", "production", "explain"] as const;

type StepDef = PipelineStep & { stage?: string; expressOnly?: boolean };

const ALL_STEPS: StepDef[] = [
  {
    id: "casting",
    label: "캐스팅",
    status: "idle",
    nodes: ["Quick Casting"],
    expressOnly: true,
  },
  {
    id: "research",
    label: "리서치/캐스팅",
    status: "idle",
    nodes: ["Research"],
    stage: "research",
  },
  {
    id: "concept",
    label: "컨셉",
    status: "idle",
    nodes: ["Critic", "Concept Gate"],
    stage: "concept",
  },
  { id: "script", label: "대본", status: "idle", nodes: ["Writer"] },
  { id: "review", label: "검증", status: "idle", nodes: ["Review", "Revise"] },
  {
    id: "production",
    label: "프로덕션",
    status: "idle",
    nodes: ["Cinematographer", "TTS Designer", "Sound Designer", "Copyright Reviewer"],
    stage: "production",
  },
  {
    id: "director",
    label: "디렉터",
    status: "idle",
    nodes: ["Director", "Human Gate"],
    stage: "production",
  },
  { id: "complete", label: "완료", status: "idle", nodes: ["Finalize", "Explain", "Learn"] },
];

const NODE_TO_STEP: Record<string, string> = {
  director_plan: "research",
  director_plan_lite: "casting",
  inventory_resolve: "casting",
  research: "research",
  critic: "concept",
  concept_gate: "concept",
  writer: "script",
  review: "review",
  revise: "review",
  cinematographer: "production",
  tts_designer: "production",
  sound_designer: "production",
  copyright_reviewer: "production",
  director: "director",
  human_gate: "director",
  finalize: "complete",
  explain: "complete",
  learn: "complete",
};

export function getInitialSteps(skipStages: string[]): PipelineStep[] {
  const skipSet = new Set(skipStages);
  const isExpress = skipSet.has("research");
  return ALL_STEPS.filter((s) => {
    if (s.stage && skipSet.has(s.stage)) return false;
    if (s.expressOnly && !isExpress) return false;
    return true;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
  }).map(({ stage: _stage, expressOnly: _eo, ...step }) => ({ ...step }));
}

export function updatePipelineSteps(
  steps: PipelineStep[],
  event: ScriptStreamEvent,
  skipStages: string[]
): PipelineStep[] {
  const stepId = NODE_TO_STEP[event.node];
  if (!stepId) {
    if (event.status === "error") {
      return steps.map((s) => (s.status === "running" ? { ...s, status: "error" } : s));
    }
    return steps;
  }

  const skipSet = new Set(skipStages);
  const isExpress = skipSet.has("research");
  const filteredIds = ALL_STEPS.filter((s) => {
    if (s.stage && skipSet.has(s.stage)) return false;
    if (s.expressOnly && !isExpress) return false;
    return true;
  }).map((s) => s.id);
  let targetIdx = filteredIds.indexOf(stepId);
  // Standard 모드에서 casting 스텝이 필터링되므로 research로 fallback
  if (targetIdx < 0 && stepId === "casting") {
    targetIdx = filteredIds.indexOf("research");
  }
  if (targetIdx < 0) return steps;

  return steps.map((s, i) => {
    if (i < targetIdx) {
      if (s.status === "error") return s; // 에러 보호
      return { ...s, status: "done" };
    }
    if (i === targetIdx) {
      if (event.status === "error") return { ...s, status: "error" };
      if (s.status === "error") return s; // 에러 보호
      if (event.status === "completed" || event.node === "learn") return { ...s, status: "done" };
      return { ...s, status: "running" };
    }
    return s;
  });
}
