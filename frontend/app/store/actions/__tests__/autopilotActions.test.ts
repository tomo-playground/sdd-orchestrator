import { describe, it, expect, vi, beforeEach } from "vitest";
import { runAutoRunFromStep } from "../autopilotActions";
import { useStoryboardStore } from "../../useStoryboardStore";
import { useContextStore } from "../../useContextStore";
import { useRenderStore } from "../../useRenderStore";
import { useUIStore } from "../../useUIStore";
import * as imageActions from "../imageActions";
import * as batchActions from "../batchActions";
import * as storyboardActions from "../storyboardActions";
import type { UseAutopilotReturn } from "../../../hooks/useAutopilot";

vi.mock("axios");
vi.mock("../imageActions");
vi.mock("../batchActions");
vi.mock("../storyboardActions");
vi.mock("../../../utils/applyAutoPin", () => ({
  applyAutoPinAfterGeneration: vi.fn(() => null),
}));
vi.mock("../../../utils/sceneSettingsResolver", () => ({
  resolveSceneMultiGen: vi.fn(() => false),
}));
vi.mock("../../selectors/projectSelectors", () => ({
  getCurrentProject: vi.fn(() => ({ name: "Test" })),
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
    image_asset_id: null,
    width: 832,
    height: 1216,
    ...overrides,
  };
}

function makeAutopilot(): UseAutopilotReturn {
  return {
    autoRunState: { status: "idle", step: "idle", message: "" },
    autoRunLog: [],
    isAutoRunning: false,
    autoRunProgress: 0,
    startRun: vi.fn(),
    setStep: vi.fn(),
    setDone: vi.fn(),
    setError: vi.fn(),
    checkCancelled: vi.fn(),
    cancel: vi.fn(),
    reset: vi.fn(),
    pushLog: vi.fn(),
    getCheckpoint: vi.fn(() => null),
    initializeFromCheckpoint: vi.fn(),
  };
}

function mockStores(scenes: ReturnType<typeof makeScene>[]) {
  const updateScene = vi.fn();
  vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
    scenes,
    updateScene,
    set: vi.fn(),
    structure: "Monologue",
  } as never);

  vi.spyOn(useContextStore, "getState").mockReturnValue({
    storyboardId: 10,
    projectId: 1,
    groupId: 2,
  } as never);

  vi.spyOn(useRenderStore, "getState").mockReturnValue({
    layoutStyle: "full",
    set: vi.fn(),
    recentVideos: [],
  } as never);

  vi.spyOn(useUIStore, "getState").mockReturnValue({
    showToast: vi.fn(),
    setActiveTab: vi.fn(),
    set: vi.fn(),
  } as never);

  return { updateScene };
}

describe("runAutoRunFromStep — image step save-on-failure", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (storyboardActions.persistStoryboard as ReturnType<typeof vi.fn>).mockResolvedValue(true);
  });

  it("saves progress before throwing when some scenes fail", async () => {
    const sceneA = makeScene({ client_id: "a", order: 0, image_url: null });
    const sceneB = makeScene({ client_id: "b", order: 1, image_url: null, id: 101 });
    mockStores([sceneA, sceneB]);

    // Batch returns: scene A succeeds, scene B fails
    (batchActions.generateBatchImages as ReturnType<typeof vi.fn>).mockResolvedValue({
      results: [
        { index: 0, status: "success" },
        { index: 1, status: "failed" },
      ],
      total: 2,
      succeeded: 1,
      failed: 1,
    });

    // After batch, scene A has image, scene B doesn't
    let _callCount = 0;
    vi.spyOn(useStoryboardStore, "getState").mockImplementation(() => {
      _callCount++;
      return {
        scenes: [
          { ...sceneA, image_url: "http://img.png", image_asset_id: 555 },
          { ...sceneB, image_url: null, image_asset_id: null },
        ],
        updateScene: vi.fn(),
        set: vi.fn(),
        structure: "Monologue",
      } as never;
    });

    // Individual retry for scene B also fails
    (imageActions.generateSceneImageFor as ReturnType<typeof vi.fn>).mockResolvedValue(null);

    const autopilot = makeAutopilot();
    await runAutoRunFromStep("images", autopilot, ["images"]);

    // persistStoryboard should be called EVEN when a scene failed
    expect(storyboardActions.persistStoryboard).toHaveBeenCalled();

    // Error should be reported
    expect(autopilot.setError).toHaveBeenCalledWith(
      "images",
      expect.stringContaining("Image failed")
    );
  });

  it("completes normally when all scenes succeed", async () => {
    const scene = makeScene({ client_id: "a", order: 0, image_url: null });
    mockStores([scene]);

    (batchActions.generateBatchImages as ReturnType<typeof vi.fn>).mockResolvedValue({
      results: [{ index: 0, status: "success" }],
      total: 1,
      succeeded: 1,
      failed: 0,
    });

    // After batch, scene has image
    vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
      scenes: [{ ...scene, image_url: "http://img.png", image_asset_id: 555 }],
      updateScene: vi.fn(),
      set: vi.fn(),
      structure: "Monologue",
    } as never);

    const autopilot = makeAutopilot();
    await runAutoRunFromStep("images", autopilot, ["images"]);

    expect(storyboardActions.persistStoryboard).toHaveBeenCalled();
    // No error when all succeed
    expect(autopilot.setError).not.toHaveBeenCalled();
    expect(autopilot.setDone).toHaveBeenCalled();
  });
});
