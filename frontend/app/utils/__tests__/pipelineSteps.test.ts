import { describe, it, expect } from "vitest";
import { getInitialSteps, applyDirectorPlan, updatePipelineSteps } from "../pipelineSteps";
import type { ScriptStreamEvent } from "../../types";

describe("getInitialSteps", () => {
  it("전체 8스텝 반환 (Director 판단 전)", () => {
    const steps = getInitialSteps();
    expect(steps).toHaveLength(8);
    expect(steps[0].id).toBe("casting");
    expect(steps[7].id).toBe("complete");
    expect(steps.every((s) => s.status === "idle")).toBe(true);
  });

  it("모든 스텝에 nodes 메타 정보 포함", () => {
    const steps = getInitialSteps();
    steps.forEach((s) => {
      expect(s.nodes).toBeDefined();
      expect(s.nodes!.length).toBeGreaterThan(0);
    });
    const production = steps.find((s) => s.id === "production");
    expect(production!.nodes).toHaveLength(4);
    expect(production!.nodes).toContain("Cinematographer");
    expect(production!.nodes).toContain("TTS Designer");
    expect(production!.nodes).toContain("Sound Designer");
    expect(production!.nodes).toContain("Copyright Reviewer");
  });

  it("매 호출 시 독립된 복사본 반환", () => {
    const a = getInitialSteps();
    const b = getInitialSteps();
    a[0].status = "done";
    expect(b[0].status).toBe("idle");
  });
});

describe("applyDirectorPlan", () => {
  it("skipStages 없음: 전체 유지", () => {
    const steps = getInitialSteps();
    const filtered = applyDirectorPlan(steps, []);
    expect(filtered).toHaveLength(8);
  });

  it("research 스킵: research 스텝 제거", () => {
    const steps = getInitialSteps();
    const filtered = applyDirectorPlan(steps, ["research"]);
    expect(filtered.find((s) => s.id === "research")).toBeUndefined();
    expect(filtered).toHaveLength(7);
  });

  it("production 스킵: production + director 스텝 제거", () => {
    const steps = getInitialSteps();
    const filtered = applyDirectorPlan(steps, ["production"]);
    expect(filtered.find((s) => s.id === "production")).toBeUndefined();
    expect(filtered.find((s) => s.id === "director")).toBeUndefined();
    expect(filtered).toHaveLength(6);
  });

  it("전체 스킵: casting + script + review + complete만 남음", () => {
    const steps = getInitialSteps();
    const filtered = applyDirectorPlan(steps, ["research", "concept", "production", "explain"]);
    expect(filtered).toHaveLength(4);
    expect(filtered[0].id).toBe("casting");
    expect(filtered[3].id).toBe("complete");
  });
});

describe("updatePipelineSteps", () => {
  const makeEvent = (node: string, status: string = "running"): ScriptStreamEvent => ({
    node,
    label: "test",
    percent: 50,
    status: status as ScriptStreamEvent["status"],
  });

  it("running 이벤트: 해당 스텝 running, 이전 스텝들 done", () => {
    const steps = getInitialSteps();
    const updated = updatePipelineSteps(steps, makeEvent("writer"));
    expect(updated[0].status).toBe("done"); // casting
    expect(updated[1].status).toBe("done"); // research
    expect(updated[2].status).toBe("done"); // concept
    expect(updated[3].status).toBe("running"); // script
    expect(updated[4].status).toBe("idle"); // review
  });

  it("error 이벤트: 해당 스텝 error", () => {
    const steps = getInitialSteps();
    const updated = updatePipelineSteps(steps, makeEvent("review", "error"));
    expect(updated[4].status).toBe("error");
  });

  it("completed 이벤트: 해당 스텝 done", () => {
    const steps = getInitialSteps();
    const updated = updatePipelineSteps(steps, makeEvent("finalize", "completed"));
    expect(updated[7].status).toBe("done"); // complete
  });

  it("learn 노드: complete 스텝 done", () => {
    const steps = getInitialSteps();
    const updated = updatePipelineSteps(steps, makeEvent("learn"));
    expect(updated[7].status).toBe("done");
  });

  it("Director 필터링 후: writer → script 스텝", () => {
    const steps = applyDirectorPlan(getInitialSteps(), [
      "research",
      "concept",
      "production",
      "explain",
    ]);
    const updated = updatePipelineSteps(steps, makeEvent("writer"));
    expect(updated[0].status).toBe("done"); // casting
    expect(updated[1].status).toBe("running"); // script
    expect(updated[2].status).toBe("idle"); // review
  });

  it("casting 필터링 시 inventory_resolve → research fallback", () => {
    const steps = applyDirectorPlan(getInitialSteps(), []);
    const updated = updatePipelineSteps(steps, makeEvent("inventory_resolve"));
    expect(updated[0].status).toBe("running"); // casting
    expect(updated[1].status).toBe("idle"); // research
  });

  it("알 수 없는 노드: 변경 없음", () => {
    const steps = getInitialSteps();
    const updated = updatePipelineSteps(steps, makeEvent("unknown_node"));
    expect(updated).toBe(steps);
  });

  it("production 병렬 노드들 모두 같은 스텝에 매핑", () => {
    const steps = getInitialSteps();
    for (const node of [
      "cinematographer",
      "tts_designer",
      "sound_designer",
      "copyright_reviewer",
    ]) {
      const updated = updatePipelineSteps(steps, makeEvent(node));
      expect(updated[5].status).toBe("running"); // production
    }
  });

  it("노드 에러 후 finalize 이벤트가 에러 스텝을 보호", () => {
    let steps = getInitialSteps();
    steps = updatePipelineSteps(steps, makeEvent("cinematographer", "error"));
    expect(steps[5].status).toBe("error"); // production

    steps = updatePipelineSteps(steps, makeEvent("finalize", "completed"));
    expect(steps[5].status).toBe("error"); // production 에러 유지
    expect(steps[6].status).toBe("done"); // director (idle → done)
    expect(steps[7].status).toBe("done"); // complete
  });

  it("production 에러 후 learn 이벤트에서도 에러 스텝 유지", () => {
    let steps = getInitialSteps();
    steps = updatePipelineSteps(steps, makeEvent("cinematographer", "error"));
    steps = updatePipelineSteps(steps, makeEvent("learn"));
    expect(steps[5].status).toBe("error"); // production 에러 유지
    expect(steps[7].status).toBe("done"); // complete
  });
});
