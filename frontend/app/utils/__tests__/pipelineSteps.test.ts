import { describe, it, expect } from "vitest";
import { getInitialSteps, updatePipelineSteps } from "../pipelineSteps";
import type { ScriptStreamEvent } from "../../types";

const SKIP_NONE: string[] = [];
const SKIP_ALL = ["research", "concept", "production", "explain"];

describe("getInitialSteps", () => {
  it("skipStages 없음: 7스텝 반환 (Standard/Creator)", () => {
    const steps = getInitialSteps(SKIP_NONE);
    expect(steps).toHaveLength(7);
    expect(steps[0].id).toBe("research");
    expect(steps[6].id).toBe("complete");
    expect(steps.every((s) => s.status === "idle")).toBe(true);
  });

  it("skipStages 4개: 3스텝 반환 (Express)", () => {
    const steps = getInitialSteps(SKIP_ALL);
    expect(steps).toHaveLength(3);
    expect(steps[0].id).toBe("script");
    expect(steps[2].id).toBe("complete");
  });

  it("skipStages 없음: 모든 스텝에 nodes 메타 정보 포함", () => {
    const steps = getInitialSteps(SKIP_NONE);
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

  it("Express: 모든 스텝에 nodes 메타 정보 포함", () => {
    const steps = getInitialSteps(SKIP_ALL);
    steps.forEach((s) => {
      expect(s.nodes).toBeDefined();
      expect(s.nodes!.length).toBeGreaterThan(0);
    });
  });

  it("매 호출 시 독립된 복사본 반환", () => {
    const a = getInitialSteps(SKIP_NONE);
    const b = getInitialSteps(SKIP_NONE);
    a[0].status = "done";
    expect(b[0].status).toBe("idle");
  });

  it("부분 스킵: research만 스킵", () => {
    const steps = getInitialSteps(["research"]);
    expect(steps).toHaveLength(6);
    expect(steps[0].id).toBe("concept");
  });

  it("부분 스킵: production만 스킵", () => {
    const steps = getInitialSteps(["production"]);
    expect(steps).toHaveLength(5);
    expect(steps.find((s) => s.id === "production")).toBeUndefined();
    expect(steps.find((s) => s.id === "director")).toBeUndefined();
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
    const steps = getInitialSteps(SKIP_NONE);
    const updated = updatePipelineSteps(steps, makeEvent("writer"), SKIP_NONE);
    expect(updated[0].status).toBe("done"); // research
    expect(updated[1].status).toBe("done"); // concept
    expect(updated[2].status).toBe("running"); // script
    expect(updated[3].status).toBe("idle"); // review
  });

  it("error 이벤트: 해당 스텝 error", () => {
    const steps = getInitialSteps(SKIP_NONE);
    const updated = updatePipelineSteps(steps, makeEvent("review", "error"), SKIP_NONE);
    expect(updated[3].status).toBe("error");
  });

  it("completed 이벤트: 해당 스텝 done", () => {
    const steps = getInitialSteps(SKIP_NONE);
    const updated = updatePipelineSteps(steps, makeEvent("finalize", "completed"), SKIP_NONE);
    expect(updated[6].status).toBe("done"); // complete
  });

  it("learn 노드: complete 스텝 done", () => {
    const steps = getInitialSteps(SKIP_NONE);
    const updated = updatePipelineSteps(steps, makeEvent("learn"), SKIP_NONE);
    expect(updated[6].status).toBe("done");
  });

  it("Express: writer → script 스텝", () => {
    const steps = getInitialSteps(SKIP_ALL);
    const updated = updatePipelineSteps(steps, makeEvent("writer"), SKIP_ALL);
    expect(updated[0].status).toBe("running"); // script
    expect(updated[1].status).toBe("idle"); // review
  });

  it("알 수 없는 노드: 변경 없음", () => {
    const steps = getInitialSteps(SKIP_NONE);
    const updated = updatePipelineSteps(steps, makeEvent("unknown_node"), SKIP_NONE);
    expect(updated).toBe(steps);
  });

  it("production 병렬 노드들 모두 같은 스텝에 매핑", () => {
    const steps = getInitialSteps(SKIP_NONE);
    for (const node of [
      "cinematographer",
      "tts_designer",
      "sound_designer",
      "copyright_reviewer",
    ]) {
      const updated = updatePipelineSteps(steps, makeEvent(node), SKIP_NONE);
      expect(updated[4].status).toBe("running"); // production
    }
  });

  it("노드 에러 후 finalize 이벤트가 에러 스텝을 보호", () => {
    let steps = getInitialSteps(SKIP_NONE);
    steps = updatePipelineSteps(steps, makeEvent("cinematographer", "error"), SKIP_NONE);
    expect(steps[4].status).toBe("error"); // production

    steps = updatePipelineSteps(steps, makeEvent("finalize", "completed"), SKIP_NONE);
    expect(steps[4].status).toBe("error"); // production 에러 유지
    expect(steps[5].status).toBe("done"); // director (idle → done)
    expect(steps[6].status).toBe("done"); // complete
  });

  it("production 에러 후 learn 이벤트에서도 에러 스텝 유지", () => {
    let steps = getInitialSteps(SKIP_NONE);
    steps = updatePipelineSteps(steps, makeEvent("cinematographer", "error"), SKIP_NONE);
    steps = updatePipelineSteps(steps, makeEvent("learn"), SKIP_NONE);
    expect(steps[4].status).toBe("error"); // production 에러 유지
    expect(steps[6].status).toBe("done"); // complete
  });
});
