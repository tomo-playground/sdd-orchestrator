import { describe, it, expect } from "vitest";
import { getInitialSteps, updatePipelineSteps } from "../pipelineSteps";
import type { ScriptStreamEvent } from "../../types";

describe("getInitialSteps", () => {
  it("full 모드: 7스텝 반환", () => {
    const steps = getInitialSteps("full");
    expect(steps).toHaveLength(7);
    expect(steps[0].id).toBe("research");
    expect(steps[6].id).toBe("complete");
    expect(steps.every((s) => s.status === "idle")).toBe(true);
  });

  it("quick 모드: 3스텝 반환", () => {
    const steps = getInitialSteps("quick");
    expect(steps).toHaveLength(3);
    expect(steps[0].id).toBe("script");
    expect(steps[2].id).toBe("complete");
  });

  it("매 호출 시 독립된 복사본 반환", () => {
    const a = getInitialSteps("full");
    const b = getInitialSteps("full");
    a[0].status = "done";
    expect(b[0].status).toBe("idle");
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
    const steps = getInitialSteps("full");
    const updated = updatePipelineSteps(steps, makeEvent("writer"), "full");
    expect(updated[0].status).toBe("done"); // research
    expect(updated[1].status).toBe("done"); // concept
    expect(updated[2].status).toBe("running"); // script
    expect(updated[3].status).toBe("idle"); // review
  });

  it("error 이벤트: 해당 스텝 error", () => {
    const steps = getInitialSteps("full");
    const updated = updatePipelineSteps(steps, makeEvent("review", "error"), "full");
    expect(updated[3].status).toBe("error");
  });

  it("completed 이벤트: 해당 스텝 done", () => {
    const steps = getInitialSteps("full");
    const updated = updatePipelineSteps(steps, makeEvent("finalize", "completed"), "full");
    expect(updated[6].status).toBe("done"); // complete
  });

  it("learn 노드: complete 스텝 done", () => {
    const steps = getInitialSteps("full");
    const updated = updatePipelineSteps(steps, makeEvent("learn"), "full");
    expect(updated[6].status).toBe("done");
  });

  it("quick 모드: writer → script 스텝", () => {
    const steps = getInitialSteps("quick");
    const updated = updatePipelineSteps(steps, makeEvent("writer"), "quick");
    expect(updated[0].status).toBe("running"); // script
    expect(updated[1].status).toBe("idle"); // review
  });

  it("알 수 없는 노드: 변경 없음", () => {
    const steps = getInitialSteps("full");
    const updated = updatePipelineSteps(steps, makeEvent("unknown_node"), "full");
    expect(updated).toBe(steps);
  });

  it("production 병렬 노드들 모두 같은 스텝에 매핑", () => {
    const steps = getInitialSteps("full");
    for (const node of ["cinematographer", "tts_designer", "sound_designer", "copyright_reviewer"]) {
      const updated = updatePipelineSteps(steps, makeEvent(node), "full");
      expect(updated[4].status).toBe("running"); // production
    }
  });
});
