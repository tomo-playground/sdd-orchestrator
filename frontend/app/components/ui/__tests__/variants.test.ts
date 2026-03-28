import { describe, it, expect } from "vitest";
import { STUDIO_2COL_LAYOUT, STUDIO_3COL_LAYOUT, RIGHT_PANEL_CLASSES } from "../variants";

describe("Studio layout constants", () => {
  it("STUDIO_2COL_LAYOUT uses 280px left column", () => {
    expect(STUDIO_2COL_LAYOUT).toContain("grid-cols-[280px_1fr]");
  });

  it("STUDIO_3COL_LAYOUT uses 240px left + 300px right columns", () => {
    expect(STUDIO_3COL_LAYOUT).toContain("grid-cols-[240px_1fr_300px]");
  });

  it("RIGHT_PANEL_CLASSES contains border-l", () => {
    expect(RIGHT_PANEL_CLASSES).toContain("border-l");
  });
});
