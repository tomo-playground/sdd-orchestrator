// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import {
  getInitialSteps,
  applyDirectorPlan,
  updatePipelineSteps,
} from "../../../app/utils/pipelineSteps";
import type { ScriptStreamEvent } from "../../../app/types";

describe("pipelineSteps", () => {
  it("maps inventory_resolve to casting step (Director 판단 전 전체 스텝)", () => {
    const steps = getInitialSteps();
    const event: ScriptStreamEvent = {
      node: "inventory_resolve",
      label: "Inventory Resolve",
      percent: 4,
      status: "running",
    };
    const updated = updatePipelineSteps(steps, event);
    const casting = updated.find((s) => s.id === "casting");
    expect(casting?.status).toBe("running");
  });

  it("excludes research step when Director skips it", () => {
    const steps = getInitialSteps();
    const filtered = applyDirectorPlan(steps, ["research"]);
    const research = filtered.find((s) => s.id === "research");
    expect(research).toBeUndefined();
  });
});
