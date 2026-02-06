import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { mapGeminiScenes, persistStoryboard, saveStoryboard } from "../storyboardActions";
import { useStudioStore } from "../../useStudioStore";

vi.mock("axios");

// Minimal store state factory
function makeStoreState(overrides: Record<string, unknown> = {}) {
  return {
    storyboardId: null as number | null,
    groupId: 1,
    scenes: [],
    topic: "Test Topic",
    description: "",
    videoCaption: null,
    setMeta: vi.fn(),
    setScenes: vi.fn(),
    showToast: vi.fn(),
    ...overrides,
  };
}

describe("mapGeminiScenes", () => {
  it("maps all fields from raw Gemini response", () => {
    const raw = [
      {
        script: "Hello world",
        speaker: "A",
        duration: 5,
        image_prompt: "1girl, smile",
        image_prompt_ko: "소녀, 미소",
        description: "A smiling girl",
        negative_prompt: "bad hands",
        _auto_pin_previous: true,
      },
    ];

    const result = mapGeminiScenes(raw, "lowres, blurry");

    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      id: 0,
      order: 1,
      script: "Hello world",
      speaker: "A",
      duration: 5,
      image_prompt: "1girl, smile",
      image_prompt_ko: "소녀, 미소",
      image_url: null,
      description: "A smiling girl",
      width: 512,
      height: 768,
      negative_prompt: "lowres, blurry, bad hands",
      isGenerating: false,
      debug_payload: "",
      _auto_pin_previous: true,
    });
  });

  it("combines base + scene negative_prompt", () => {
    const raw = [{ negative_prompt: "extra_fingers" }];
    const result = mapGeminiScenes(raw, "lowres");
    expect(result[0].negative_prompt).toBe("lowres, extra_fingers");
  });

  it("handles empty scene negative_prompt", () => {
    const raw = [{}];
    const result = mapGeminiScenes(raw, "lowres");
    expect(result[0].negative_prompt).toBe("lowres");
  });

  it("handles empty base negative", () => {
    const raw = [{ negative_prompt: "bad" }];
    const result = mapGeminiScenes(raw, "");
    expect(result[0].negative_prompt).toBe("bad");
  });

  it("handles both negatives empty", () => {
    const raw = [{}];
    const result = mapGeminiScenes(raw, "");
    expect(result[0].negative_prompt).toBe("");
  });

  it("returns empty array for empty input", () => {
    expect(mapGeminiScenes([], "lowres")).toEqual([]);
  });

  it("provides defaults for missing fields", () => {
    const raw = [{}];
    const result = mapGeminiScenes(raw, "");

    expect(result[0].script).toBe("");
    expect(result[0].speaker).toBe("Narrator");
    expect(result[0].duration).toBe(3);
    expect(result[0].image_prompt).toBe("");
    expect(result[0].description).toBe("");
  });

  it("assigns sequential ids and orders for multiple scenes", () => {
    const raw = [{}, {}, {}];
    const result = mapGeminiScenes(raw, "");

    expect(result.map((s) => s.id)).toEqual([0, 1, 2]);
    expect(result.map((s) => s.order)).toEqual([1, 2, 3]);
  });

  it("maps _auto_pin_previous true from backend", () => {
    const raw = [{ _auto_pin_previous: true }];
    const result = mapGeminiScenes(raw, "");
    expect(result[0]._auto_pin_previous).toBe(true);
  });

  it("maps _auto_pin_previous false from backend", () => {
    const raw = [{ _auto_pin_previous: false }];
    const result = mapGeminiScenes(raw, "");
    expect(result[0]._auto_pin_previous).toBe(false);
  });

  it("defaults _auto_pin_previous to false when missing", () => {
    const raw = [{}];
    const result = mapGeminiScenes(raw, "");
    expect(result[0]._auto_pin_previous).toBe(false);
  });

  it("handles mixed _auto_pin_previous values across scenes", () => {
    const raw = [
      { _auto_pin_previous: false }, // first scene (location change)
      { _auto_pin_previous: true }, // same location
      { _auto_pin_previous: false }, // location change
      { _auto_pin_previous: true }, // same location
    ];
    const result = mapGeminiScenes(raw, "");
    expect(result.map((s) => s._auto_pin_previous)).toEqual([false, true, false, true]);
  });
});

describe("persistStoryboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns false when no scenes", async () => {
    vi.spyOn(useStudioStore, "getState").mockReturnValue(makeStoreState({ scenes: [] }) as never);
    expect(await persistStoryboard()).toBe(false);
  });

  it("returns false when no groupId", async () => {
    vi.spyOn(useStudioStore, "getState").mockReturnValue(
      makeStoreState({ groupId: null, scenes: [{ id: 0 }] }) as never
    );
    expect(await persistStoryboard()).toBe(false);
  });

  it("calls PUT when storyboardId exists", async () => {
    const state = makeStoreState({
      storyboardId: 42,
      scenes: [
        {
          id: 0,
          script: "test",
          speaker: "Narrator",
          duration: 3,
          image_prompt: "prompt",
          image_prompt_ko: "",
          image_url: null,
          description: "",
          width: 512,
          height: 768,
          negative_prompt: "",
          context_tags: undefined,
        },
      ],
    });
    vi.spyOn(useStudioStore, "getState").mockReturnValue(state as never);
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: {} });

    const result = await persistStoryboard();

    expect(result).toBe(true);
    expect(axios.put).toHaveBeenCalledWith(
      expect.stringContaining("/storyboards/42"),
      expect.objectContaining({ title: "Test Topic" })
    );
    expect(axios.post).not.toHaveBeenCalled();
  });

  it("calls POST when no storyboardId and reassigns scene IDs", async () => {
    const setMeta = vi.fn();
    const setScenes = vi.fn();
    const scenes = [
      {
        id: 0,
        script: "test",
        speaker: "Narrator",
        duration: 3,
        image_prompt: "",
        image_prompt_ko: "",
        image_url: null,
        description: "",
        width: 512,
        height: 768,
        negative_prompt: "",
      },
    ];
    const state = makeStoreState({ storyboardId: null, scenes, setMeta, setScenes });
    vi.spyOn(useStudioStore, "getState").mockReturnValue(state as never);
    (axios.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { storyboard_id: 99, scene_ids: [501] },
    });

    const result = await persistStoryboard();

    expect(result).toBe(true);
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining("/storyboards"),
      expect.objectContaining({ title: "Test Topic" })
    );
    expect(setMeta).toHaveBeenCalledWith({ storyboardId: 99, storyboardTitle: "Test Topic" });
    expect(setScenes).toHaveBeenCalledWith([expect.objectContaining({ id: 501 })]);
  });

  it("returns false on API error", async () => {
    const state = makeStoreState({
      storyboardId: 1,
      scenes: [{ id: 0 }],
    });
    vi.spyOn(useStudioStore, "getState").mockReturnValue(state as never);
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Network error")
    );

    const result = await persistStoryboard();
    expect(result).toBe(false);
  });
});

describe("saveStoryboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows error toast when no scenes", async () => {
    const showToast = vi.fn();
    vi.spyOn(useStudioStore, "getState").mockReturnValue(
      makeStoreState({ scenes: [], showToast }) as never
    );

    const result = await saveStoryboard();

    expect(result).toBe(false);
    expect(showToast).toHaveBeenCalledWith("No scenes to save", "error");
  });

  it("shows error toast when no groupId", async () => {
    const showToast = vi.fn();
    vi.spyOn(useStudioStore, "getState").mockReturnValue(
      makeStoreState({ groupId: null, scenes: [{ id: 0 }], showToast }) as never
    );

    const result = await saveStoryboard();

    expect(result).toBe(false);
    expect(showToast).toHaveBeenCalledWith("Create a group to save your storyboard", "error");
  });

  it("shows success toast for update (existing storyboardId)", async () => {
    const showToast = vi.fn();
    const state = makeStoreState({
      storyboardId: 42,
      scenes: [{ id: 0, script: "test" }],
      showToast,
    });
    vi.spyOn(useStudioStore, "getState").mockReturnValue(state as never);
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: {} });

    const result = await saveStoryboard();

    expect(result).toBe(true);
    expect(showToast).toHaveBeenCalledWith("Storyboard updated", "success");
  });

  it("shows success toast for new save (no storyboardId)", async () => {
    const showToast = vi.fn();
    const state = makeStoreState({
      storyboardId: null,
      scenes: [{ id: 0 }],
      showToast,
    });
    vi.spyOn(useStudioStore, "getState").mockReturnValue(state as never);
    (axios.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { storyboard_id: 10, scene_ids: [100] },
    });

    const result = await saveStoryboard();

    expect(result).toBe(true);
    expect(showToast).toHaveBeenCalledWith("Storyboard saved", "success");
  });

  it("shows error toast on failure", async () => {
    const showToast = vi.fn();
    const state = makeStoreState({
      storyboardId: 1,
      scenes: [{ id: 0 }],
      showToast,
    });
    vi.spyOn(useStudioStore, "getState").mockReturnValue(state as never);
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("fail"));

    const result = await saveStoryboard();

    expect(result).toBe(false);
    expect(showToast).toHaveBeenCalledWith("Failed to save storyboard", "error");
  });
});
