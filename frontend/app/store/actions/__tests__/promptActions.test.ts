import { describe, it, expect, vi, beforeEach } from "vitest";
import { buildNegativePrompt, buildScenePrompt } from "../promptActions";
import { useStoryboardStore } from "../../useStoryboardStore";

vi.mock("../../../utils/speakerResolver", () => ({
  resolveNegativePromptForSpeaker: vi.fn(
    (_speaker: string, negA: string, _negB: string) => negA
  ),
}));

describe("buildScenePrompt", () => {
  it("returns trimmed image_prompt", () => {
    const scene = { image_prompt: "  1girl, smile  " } as never;
    expect(buildScenePrompt(scene)).toBe("1girl, smile");
  });

  it("returns null for empty image_prompt", () => {
    const scene = { image_prompt: "" } as never;
    expect(buildScenePrompt(scene)).toBeNull();
  });

  it("returns null for whitespace-only image_prompt", () => {
    const scene = { image_prompt: "   " } as never;
    expect(buildScenePrompt(scene)).toBeNull();
  });
});

describe("buildNegativePrompt", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
      baseNegativePromptA: "lowres, blurry",
      baseNegativePromptB: "",
    } as never);
  });

  it("combines base and scene negative prompts", () => {
    const scene = { speaker: "A", negative_prompt: "bad hands" } as never;
    const result = buildNegativePrompt(scene);
    expect(result).toBe("lowres, blurry, bad hands");
  });

  it("returns base only when scene negative is empty", () => {
    const scene = { speaker: "A", negative_prompt: "" } as never;
    const result = buildNegativePrompt(scene);
    expect(result).toBe("lowres, blurry");
  });

  it("returns scene negative only when base is empty", () => {
    vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
      baseNegativePromptA: "",
      baseNegativePromptB: "",
    } as never);
    const scene = { speaker: "A", negative_prompt: "bad hands" } as never;
    const result = buildNegativePrompt(scene);
    expect(result).toBe("bad hands");
  });

  it("deduplicates tokens", () => {
    const scene = { speaker: "A", negative_prompt: "lowres, extra" } as never;
    const result = buildNegativePrompt(scene);
    // "lowres, blurry, lowres, extra" → deduped to "lowres, blurry, extra"
    expect(result).toBe("lowres, blurry, extra");
  });
});
