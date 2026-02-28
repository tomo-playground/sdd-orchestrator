import type { PipelineStep, ScriptStreamEvent } from "../types";

type StepDef = PipelineStep & { stage?: string };

const ALL_STEPS: StepDef[] = [
  {
    id: "casting",
    label: "캐릭터 분석 중",
    status: "idle",
    nodes: ["Quick Casting"],
  },
  {
    id: "research",
    label: "자료 조사 중",
    status: "idle",
    nodes: ["Research"],
    stage: "research",
  },
  {
    id: "concept",
    label: "컨셉 구상 중",
    status: "idle",
    nodes: ["Critic", "Concept Gate"],
    stage: "concept",
  },
  { id: "script", label: "대본 작성 중", status: "idle", nodes: ["Writer"] },
  { id: "review", label: "품질 검증 중", status: "idle", nodes: ["Review", "Revise"] },
  {
    id: "production",
    label: "연출 설정 중",
    status: "idle",
    nodes: ["Cinematographer", "TTS Designer", "Sound Designer", "Copyright Reviewer"],
    stage: "production",
  },
  {
    id: "director",
    label: "최종 검토 중",
    status: "idle",
    nodes: ["Director", "Human Gate"],
    stage: "production",
  },
  { id: "complete", label: "마무리 중", status: "idle", nodes: ["Finalize", "Explain", "Learn"] },
];

const NODE_TO_STEP: Record<string, string> = {
  director_plan: "casting",
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

/** Director 판단 전: 모든 스텝을 표시 */
export function getInitialSteps(): PipelineStep[] {
  return ALL_STEPS.map(({ stage: _stage, ...step }) => ({ ...step }));
}

/** Director 결정 수신 후: skipStages 기반 스텝 필터링 */
export function applyDirectorPlan(steps: PipelineStep[], skipStages: string[]): PipelineStep[] {
  const skipSet = new Set(skipStages);
  return steps.filter((s) => {
    const def = ALL_STEPS.find((d) => d.id === s.id);
    return !def?.stage || !skipSet.has(def.stage);
  });
}

export function updatePipelineSteps(
  steps: PipelineStep[],
  event: ScriptStreamEvent
): PipelineStep[] {
  const stepId = NODE_TO_STEP[event.node];
  if (!stepId) {
    if (event.status === "error") {
      return steps.map((s) => (s.status === "running" ? { ...s, status: "error" } : s));
    }
    return steps;
  }

  const stepIds = steps.map((s) => s.id);
  let targetIdx = stepIds.indexOf(stepId);
  // casting 스텝이 Director에 의해 필터링된 경우 research로 fallback
  if (targetIdx < 0 && stepId === "casting") {
    targetIdx = stepIds.indexOf("research");
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
