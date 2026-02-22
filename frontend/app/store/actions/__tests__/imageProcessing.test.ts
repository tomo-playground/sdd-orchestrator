import { describe, it, expect, vi, beforeEach } from "vitest";
import type { ProcessOpts } from "../imageProcessing";
import { useContextStore } from "../../useContextStore";
import { useStoryboardStore } from "../../useStoryboardStore";
import { useUIStore } from "../../useUIStore";

vi.mock("axios");

// Minimal mock stores
beforeEach(() => {
  vi.spyOn(useContextStore, "getState").mockReturnValue({
    projectId: 1,
    groupId: 1,
    storyboardId: 10,
  } as ReturnType<typeof useContextStore.getState>);

  vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
    imageValidationResults: {},
    set: vi.fn(),
  } as unknown as ReturnType<typeof useStoryboardStore.getState>);

  vi.spyOn(useUIStore, "getState").mockReturnValue({
    showToast: vi.fn(),
  } as unknown as ReturnType<typeof useUIStore.getState>);
});

describe("ProcessOpts controlnet fields", () => {
  it("accepts controlnet_pose and ip_adapter_reference", () => {
    const opts: ProcessOpts = {
      images: ["base64data"],
      scene: { id: 1, client_id: "s1" } as ProcessOpts["scene"],
      prompt: "1girl, standing",
      selectedCharacterId: null,
      silent: true,
      controlnet_pose: "standing",
      ip_adapter_reference: "char_ref",
    };
    expect(opts.controlnet_pose).toBe("standing");
    expect(opts.ip_adapter_reference).toBe("char_ref");
  });

  it("allows controlnet fields to be undefined", () => {
    const opts: ProcessOpts = {
      images: ["base64data"],
      scene: { id: 1, client_id: "s1" } as ProcessOpts["scene"],
      prompt: "1girl",
      selectedCharacterId: null,
      silent: true,
    };
    expect(opts.controlnet_pose).toBeUndefined();
    expect(opts.ip_adapter_reference).toBeUndefined();
  });

  it("does not require autoComposePrompt (removed in compose refactor)", () => {
    const opts: ProcessOpts = {
      images: ["base64data"],
      scene: { id: 1, client_id: "s1" } as ProcessOpts["scene"],
      prompt: "1girl",
      selectedCharacterId: 1,
      silent: false,
    };
    expect(opts.selectedCharacterId).toBe(1);
    // autoComposePrompt is no longer part of ProcessOpts
    expect("autoComposePrompt" in opts).toBe(false);
  });
});
