import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { generateBatchImages } from "../batchActions";
import { useStoryboardStore } from "../../useStoryboardStore";
import { useContextStore } from "../../useContextStore";
import * as imageActions from "../imageActions";

vi.mock("axios");
vi.mock("../imageActions", () => ({
  storeSceneImage: vi.fn(),
}));
vi.mock("../promptActions", () => ({
  buildScenePrompt: vi.fn(() => "1girl"),
  buildNegativePrompt: vi.fn(() => "lowres"),
}));
vi.mock("../../../utils/speakerResolver", () => ({
  resolveCharacterIdForSpeaker: vi.fn(() => 1),
}));
vi.mock("../../../utils/sceneSettingsResolver", () => ({
  resolveSceneControlnet: vi.fn(() => ({ enabled: false, weight: 1 })),
  resolveSceneIpAdapter: vi.fn(() => ({ enabled: false, weight: 0.7, reference: null })),
}));

function makeScene(overrides: Record<string, unknown> = {}) {
  return {
    id: 100,
    client_id: "scene-a",
    order: 0,
    script: "test",
    speaker: "Narrator" as const,
    duration: 3,
    image_prompt: "1girl",
    image_url: null,
    width: 832,
    height: 1216,
    use_reference_only: true,
    reference_only_weight: 0.5,
    environment_reference_id: null,
    environment_reference_weight: 0.3,
    ...overrides,
  };
}

describe("generateBatchImages", () => {
  let updateScene: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    updateScene = vi.fn();

    const scene = makeScene();
    vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
      scenes: [scene],
      updateScene,
    } as never);

    vi.spyOn(useContextStore, "getState").mockReturnValue({
      projectId: 1,
      groupId: 2,
      storyboardId: 10,
    } as never);
  });

  it("sets candidates with media_asset_id after successful store", async () => {
    (axios.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        results: [{ index: 0, status: "success", data: { image: "base64data" } }],
        total: 1,
        succeeded: 1,
        failed: 0,
      },
    });

    (imageActions.storeSceneImage as ReturnType<typeof vi.fn>).mockResolvedValue({
      url: "http://localhost:9000/img.png",
      asset_id: 555,
    });

    await generateBatchImages(["scene-a"]);

    // Check that updateScene was called with candidates
    const updates = updateScene.mock.calls.map(
      (c: [string, Record<string, unknown>]) => c[1]
    );
    const finalUpdate = updates.find(
      (u: Record<string, unknown>) => u.image_url !== undefined
    );

    expect(finalUpdate).toBeDefined();
    expect(finalUpdate.image_asset_id).toBe(555);
    expect(finalUpdate.candidates).toEqual([
      { media_asset_id: 555, image_url: "http://localhost:9000/img.png" },
    ]);
  });

  it("does not set candidates when asset_id is missing", async () => {
    (axios.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        results: [{ index: 0, status: "success", data: { image: "base64data" } }],
        total: 1,
        succeeded: 1,
        failed: 0,
      },
    });

    (imageActions.storeSceneImage as ReturnType<typeof vi.fn>).mockResolvedValue({
      url: "data:image/png;base64,xxx",
      asset_id: null,
    });

    await generateBatchImages(["scene-a"]);

    const updates = updateScene.mock.calls.map(
      (c: [string, Record<string, unknown>]) => c[1]
    );
    const finalUpdate = updates.find(
      (u: Record<string, unknown>) => u.image_url !== undefined
    );

    expect(finalUpdate).toBeDefined();
    expect(finalUpdate.image_asset_id).toBeNull();
    expect(finalUpdate.candidates).toBeUndefined();
  });

  it("returns null for empty scene list", async () => {
    const result = await generateBatchImages([]);
    expect(result).toBeNull();
  });
});
