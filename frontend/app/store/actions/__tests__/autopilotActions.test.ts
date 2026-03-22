import { describe, it, expect, vi, beforeEach } from "vitest";
import { runAutoRunFromStep } from "../autopilotActions";
import { useStoryboardStore } from "../../useStoryboardStore";
import { useContextStore } from "../../useContextStore";
import { useRenderStore } from "../../useRenderStore";
import { useUIStore } from "../../useUIStore";
import * as imageActions from "../imageActions";
import * as storyboardActions from "../storyboardActions";
import type { UseAutopilotReturn } from "../../../hooks/useAutopilot";

vi.mock("axios");
vi.mock("../imageActions");
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
    structure: "monologue",
    imageGenProgress: {},
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

describe("runAutoRunFromStep — image step (individual SSE)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (storyboardActions.persistStoryboard as ReturnType<typeof vi.fn>).mockResolvedValue(true);
  });

  it("calls generateSceneImageFor for each singleGen scene", async () => {
    const sceneA = makeScene({ client_id: "a", order: 0, image_url: null });
    const sceneB = makeScene({ client_id: "b", order: 1, image_url: null, id: 101 });
    mockStores([sceneA, sceneB]);

    (imageActions.generateSceneImageFor as ReturnType<typeof vi.fn>).mockResolvedValue({
      image_url: "http://img.png",
      image_asset_id: 555,
    });

    const autopilot = makeAutopilot();
    await runAutoRunFromStep("images", autopilot, ["images"]);

    // Each scene should trigger generateSceneImageFor
    expect(imageActions.generateSceneImageFor).toHaveBeenCalledTimes(2);
    expect(storyboardActions.persistStoryboard).toHaveBeenCalled();
    expect(autopilot.setDone).toHaveBeenCalled();
    expect(autopilot.setError).not.toHaveBeenCalled();
  });

  it("saves progress before throwing when some scenes fail", async () => {
    const sceneA = makeScene({ client_id: "a", order: 0, image_url: null });
    const sceneB = makeScene({ client_id: "b", order: 1, image_url: null, id: 101 });
    mockStores([sceneA, sceneB]);

    // Scene A succeeds, scene B fails
    (imageActions.generateSceneImageFor as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ image_url: "http://img.png", image_asset_id: 555 })
      .mockResolvedValueOnce(null);

    const autopilot = makeAutopilot();
    await runAutoRunFromStep("images", autopilot, ["images"]);

    // persistStoryboard should be called EVEN when a scene failed
    expect(storyboardActions.persistStoryboard).toHaveBeenCalled();

    // Error should be reported
    expect(autopilot.setError).toHaveBeenCalledWith(
      "images",
      expect.stringContaining("Image failed"),
    );
  });

  it("completes normally when all scenes succeed", async () => {
    const scene = makeScene({ client_id: "a", order: 0, image_url: null });
    mockStores([scene]);

    (imageActions.generateSceneImageFor as ReturnType<typeof vi.fn>).mockResolvedValue({
      image_url: "http://img.png",
      image_asset_id: 555,
    });

    const autopilot = makeAutopilot();
    await runAutoRunFromStep("images", autopilot, ["images"]);

    expect(storyboardActions.persistStoryboard).toHaveBeenCalled();
    expect(autopilot.setError).not.toHaveBeenCalled();
    expect(autopilot.setDone).toHaveBeenCalled();
  });

  it("isolates failures — only failed scenes go to failedSceneOrders", async () => {
    const scenes = [
      makeScene({ client_id: "a", order: 0, image_url: null }),
      makeScene({ client_id: "b", order: 1, image_url: null, id: 101 }),
      makeScene({ client_id: "c", order: 2, image_url: null, id: 102 }),
    ];
    mockStores(scenes);

    // Scenes a and c succeed, b fails
    (imageActions.generateSceneImageFor as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ image_url: "http://a.png", image_asset_id: 1 })
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({ image_url: "http://c.png", image_asset_id: 3 });

    const autopilot = makeAutopilot();
    await runAutoRunFromStep("images", autopilot, ["images"]);

    // Error message should only mention scene #2 (order 1)
    expect(autopilot.setError).toHaveBeenCalledWith(
      "images",
      expect.stringContaining("#2"),
    );
    // Should indicate 2 saved
    expect(autopilot.setError).toHaveBeenCalledWith(
      "images",
      expect.stringContaining("2 saved"),
    );
  });

  it("skips scenes that already have images", async () => {
    const sceneA = makeScene({ client_id: "a", order: 0, image_url: "http://existing.png" });
    const sceneB = makeScene({ client_id: "b", order: 1, image_url: null, id: 101 });
    mockStores([sceneA, sceneB]);

    (imageActions.generateSceneImageFor as ReturnType<typeof vi.fn>).mockResolvedValue({
      image_url: "http://img.png",
      image_asset_id: 555,
    });

    const autopilot = makeAutopilot();
    await runAutoRunFromStep("images", autopilot, ["images"]);

    // Only scene B (no image) should trigger generation
    expect(imageActions.generateSceneImageFor).toHaveBeenCalledTimes(1);
  });

  it("runs at most AUTORUN_CONCURRENCY=2 scenes simultaneously", async () => {
    const scenes = [
      makeScene({ client_id: "a", order: 0, image_url: null }),
      makeScene({ client_id: "b", order: 1, image_url: null, id: 101 }),
      makeScene({ client_id: "c", order: 2, image_url: null, id: 102 }),
    ];
    mockStores(scenes);

    let concurrentCount = 0;
    let maxConcurrentObserved = 0;

    (imageActions.generateSceneImageFor as ReturnType<typeof vi.fn>).mockImplementation(
      async () => {
        concurrentCount++;
        maxConcurrentObserved = Math.max(maxConcurrentObserved, concurrentCount);
        await new Promise((resolve) => setTimeout(resolve, 10));
        concurrentCount--;
        return { image_url: "http://img.png", image_asset_id: 555 };
      },
    );

    const autopilot = makeAutopilot();
    await runAutoRunFromStep("images", autopilot, ["images"]);

    expect(maxConcurrentObserved).toBeLessThanOrEqual(2);
    expect(imageActions.generateSceneImageFor).toHaveBeenCalledTimes(3);
  });
});
