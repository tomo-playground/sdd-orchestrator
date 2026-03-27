import { describe, it, expect } from "vitest";
import { deriveProgressStep } from "../home/ContinueWorkingSection";

type SbInput = Parameters<typeof deriveProgressStep>[0];

function makeSb(overrides: Partial<SbInput> = {}): SbInput {
  return {
    id: 1,
    title: "Test",
    scene_count: 3,
    image_count: 0,
    kanban_status: "draft",
    stage_status: null,
    updated_at: null,
    ...overrides,
  };
}

describe("deriveProgressStep", () => {
  it("returns 'script' for draft status", () => {
    expect(deriveProgressStep(makeSb({ kanban_status: "draft" }))).toBe("script");
  });

  it("returns 'stage' when stage_status is staged", () => {
    expect(deriveProgressStep(makeSb({ kanban_status: "draft", stage_status: "staged" }))).toBe(
      "stage"
    );
  });

  it("returns 'stage' when stage_status is staging", () => {
    expect(deriveProgressStep(makeSb({ kanban_status: "draft", stage_status: "staging" }))).toBe(
      "stage"
    );
  });

  it("returns 'stage' when stage_status is failed", () => {
    expect(deriveProgressStep(makeSb({ kanban_status: "draft", stage_status: "failed" }))).toBe(
      "stage"
    );
  });

  it("returns 'script' when stage_status is pending (not yet started)", () => {
    expect(deriveProgressStep(makeSb({ kanban_status: "draft", stage_status: "pending" }))).toBe(
      "script"
    );
  });

  it("returns 'images' when in_prod and image_count > 0", () => {
    expect(deriveProgressStep(makeSb({ kanban_status: "in_prod", image_count: 2 }))).toBe("images");
  });

  it("returns 'script' when in_prod but image_count is 0", () => {
    expect(deriveProgressStep(makeSb({ kanban_status: "in_prod", image_count: 0 }))).toBe("script");
  });

  it("returns 'stage' when in_prod with image_count 0 but stage_status staged", () => {
    expect(
      deriveProgressStep(
        makeSb({ kanban_status: "in_prod", image_count: 0, stage_status: "staged" })
      )
    ).toBe("stage");
  });

  it("returns 'render' for rendered status", () => {
    expect(deriveProgressStep(makeSb({ kanban_status: "rendered" }))).toBe("render");
  });

  it("returns 'done' for published status", () => {
    expect(deriveProgressStep(makeSb({ kanban_status: "published" }))).toBe("done");
  });

  it("prioritizes published over stage_status", () => {
    expect(deriveProgressStep(makeSb({ kanban_status: "published", stage_status: "staged" }))).toBe(
      "done"
    );
  });

  it("prioritizes rendered over stage_status", () => {
    expect(deriveProgressStep(makeSb({ kanban_status: "rendered", stage_status: "staged" }))).toBe(
      "render"
    );
  });
});
