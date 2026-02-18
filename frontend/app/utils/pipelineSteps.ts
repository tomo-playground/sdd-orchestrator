import type { PipelineStep, ScriptStreamEvent } from "../types";

// ── Full 모드 7스텝 ──
const FULL_STEPS: PipelineStep[] = [
  { id: "research", label: "리서치", status: "idle", nodes: ["Research"] },
  { id: "concept", label: "컨셉", status: "idle", nodes: ["Critic", "Concept Gate"] },
  { id: "script", label: "대본", status: "idle", nodes: ["Writer"] },
  { id: "review", label: "검증", status: "idle", nodes: ["Review", "Revise"] },
  {
    id: "production",
    label: "프로덕션",
    status: "idle",
    nodes: ["Cinematographer", "TTS Designer", "Sound Designer", "Copyright Reviewer"],
  },
  { id: "director", label: "디렉터", status: "idle", nodes: ["Director", "Human Gate"] },
  { id: "complete", label: "완료", status: "idle", nodes: ["Finalize", "Explain", "Learn"] },
];

// ── Quick 모드 3스텝 ──
const QUICK_STEPS: PipelineStep[] = [
  { id: "script", label: "대본", status: "idle", nodes: ["Writer"] },
  { id: "review", label: "검증", status: "idle", nodes: ["Review", "Revise"] },
  { id: "complete", label: "완료", status: "idle", nodes: ["Finalize"] },
];

// ── 15 노드 → 논리 스텝 매핑 ──
const NODE_TO_STEP: Record<string, string> = {
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

export function getInitialSteps(mode: "quick" | "full"): PipelineStep[] {
  const template = mode === "full" ? FULL_STEPS : QUICK_STEPS;
  return template.map((s) => ({ ...s }));
}

export function updatePipelineSteps(
  steps: PipelineStep[],
  event: ScriptStreamEvent,
  mode: "quick" | "full"
): PipelineStep[] {
  const stepId = NODE_TO_STEP[event.node];
  if (!stepId) return steps;

  const stepIds = (mode === "full" ? FULL_STEPS : QUICK_STEPS).map((s) => s.id);
  const targetIdx = stepIds.indexOf(stepId);
  if (targetIdx < 0) return steps;

  return steps.map((s, i) => {
    if (i < targetIdx) return { ...s, status: "done" };
    if (i === targetIdx) {
      if (event.status === "error") return { ...s, status: "error" };
      if (event.status === "completed" || event.node === "learn") return { ...s, status: "done" };
      return { ...s, status: "running" };
    }
    return s;
  });
}
