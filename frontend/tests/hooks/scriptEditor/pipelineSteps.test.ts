// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { getInitialSteps, updatePipelineSteps } from "../../../app/utils/pipelineSteps";
import type { ScriptStreamEvent } from "../../../app/types";

describe("pipelineSteps", () => {
  it("maps inventory_resolve to research step", () => {
    const steps = getInitialSteps([]);
    const event: ScriptStreamEvent = {
      node: "inventory_resolve",
      label: "Inventory Resolve",
      percent: 4,
      status: "running",
    };
    const updated = updatePipelineSteps(steps, event, []);
    const research = updated.find((s) => s.id === "research");
    expect(research?.status).toBe("running");
  });

  it("research step label includes 캐스팅", () => {
    const steps = getInitialSteps([]);
    const research = steps.find((s) => s.id === "research");
    expect(research?.label).toContain("캐스팅");
  });

  it("excludes research step when skipped", () => {
    const steps = getInitialSteps(["research"]);
    const research = steps.find((s) => s.id === "research");
    expect(research).toBeUndefined();
  });
});
