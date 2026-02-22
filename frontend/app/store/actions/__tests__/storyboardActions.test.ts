import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import {
  mapGeminiScenes,
  persistStoryboard,
  saveStoryboard,
  sanitizeCandidatesForDb,
} from "../storyboardActions";
import { useContextStore } from "../../useContextStore";
import { useStoryboardStore } from "../../useStoryboardStore";
import { useUIStore } from "../../useUIStore";
import { useRenderStore } from "../../useRenderStore";

vi.mock("axios");

// Default mock state factories per store
function makeContextState(overrides: Record<string, unknown> = {}) {
  return {
    storyboardId: null as number | null,
    groupId: 1,
    setContext: vi.fn(),
    ...overrides,
  };
}

function makeStoryboardState(overrides: Record<string, unknown> = {}) {
  return {
    scenes: [],
    topic: "Test Topic",
    description: "",
    currentSceneIndex: 0,
    setScenes: vi.fn(),
    set: vi.fn(),
    ...overrides,
  };
}

function makeUIState(overrides: Record<string, unknown> = {}) {
  return {
    showToast: vi.fn(),
    set: vi.fn(),
    ...overrides,
  };
}

function makeRenderState(overrides: Record<string, unknown> = {}) {
  return {
    videoCaption: null,
    ...overrides,
  };
}

/** Helper to mock all 4 stores at once from a flat overrides object */
function mockAllStores(overrides: Record<string, unknown> = {}) {
  const {
    storyboardId,
    groupId,
    setContext,
    scenes,
    topic,
    description,
    currentSceneIndex,
    setScenes,
    setCurrentSceneIndex,
    showToast,
    videoCaption,
    ...rest
  } = overrides;

  const ctxOverrides: Record<string, unknown> = {};
  if (storyboardId !== undefined) ctxOverrides.storyboardId = storyboardId;
  if (groupId !== undefined) ctxOverrides.groupId = groupId;
  if (setContext !== undefined) ctxOverrides.setContext = setContext;

  const sbOverrides: Record<string, unknown> = {};
  if (scenes !== undefined) sbOverrides.scenes = scenes;
  if (topic !== undefined) sbOverrides.topic = topic;
  if (description !== undefined) sbOverrides.description = description;
  if (currentSceneIndex !== undefined) sbOverrides.currentSceneIndex = currentSceneIndex;
  if (setScenes !== undefined) sbOverrides.setScenes = setScenes;
  if (setCurrentSceneIndex !== undefined) sbOverrides.set = setCurrentSceneIndex;

  const uiOverrides: Record<string, unknown> = {};
  if (showToast !== undefined) uiOverrides.showToast = showToast;

  const renderOverrides: Record<string, unknown> = {};
  if (videoCaption !== undefined) renderOverrides.videoCaption = videoCaption;

  // Spread any extra fields into storyboard store for flexibility
  Object.assign(sbOverrides, rest);

  const ctxState = makeContextState(ctxOverrides);
  const sbState = makeStoryboardState(sbOverrides);
  const uiState = makeUIState(uiOverrides);
  const renderState = makeRenderState(renderOverrides);

  vi.spyOn(useContextStore, "getState").mockReturnValue(ctxState as never);
  vi.spyOn(useStoryboardStore, "getState").mockReturnValue(sbState as never);
  vi.spyOn(useUIStore, "getState").mockReturnValue(uiState as never);
  vi.spyOn(useRenderStore, "getState").mockReturnValue(renderState as never);

  return { ctxState, sbState, uiState, renderState };
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
        negative_prompt: "bad hands",
        _auto_pin_previous: true,
      },
    ];

    const result = mapGeminiScenes(raw, "lowres, blurry");

    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      id: 0,
      order: 0,
      client_id: expect.any(String),
      script: "Hello world",
      speaker: "A",
      duration: 5,
      image_prompt: "1girl, smile",
      image_prompt_ko: "소녀, 미소",
      image_url: null,
      width: 512,
      height: 768,
      negative_prompt: "lowres, blurry, bad hands",
      context_tags: undefined,
      character_actions: undefined,
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
  });

  it("assigns sequential ids and orders for multiple scenes", () => {
    const raw = [{}, {}, {}];
    const result = mapGeminiScenes(raw, "");

    expect(result.map((s) => s.id)).toEqual([0, 0, 0]);
    expect(result.map((s) => s.order)).toEqual([0, 1, 2]);
  });

  it("uses 0-indexed order matching backend create_scenes convention", () => {
    const raw = [{ script: "First" }, { script: "Second" }, { script: "Third" }];
    const result = mapGeminiScenes(raw, "");

    // order must be 0-indexed to match backend create_scenes(order=idx)
    expect(result[0].order).toBe(0);
    expect(result[1].order).toBe(1);
    expect(result[2].order).toBe(2);
    // id also 0-indexed
    expect(result[0].id).toBe(0);
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
    mockAllStores({ scenes: [] });
    expect(await persistStoryboard()).toBe(false);
  });

  it("returns false when no groupId", async () => {
    mockAllStores({ groupId: null, scenes: [{ id: 0 }] });
    expect(await persistStoryboard()).toBe(false);
  });

  it("calls PUT when storyboardId exists and updates scene IDs", async () => {
    const setScenes = vi.fn();
    mockAllStores({
      storyboardId: 42,
      setScenes,
      scenes: [
        {
          id: 100, // Old scene ID
          script: "test",
          speaker: "Narrator",
          duration: 3,
          image_prompt: "prompt",
          image_prompt_ko: "",
          image_url: null,
          width: 512,
          height: 768,
          negative_prompt: "",
          context_tags: undefined,
        },
      ],
    });
    // PUT now returns scene_ids (scenes are deleted and recreated)
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [200] },
    });

    const result = await persistStoryboard();

    expect(result).toBe(true);
    expect(axios.put).toHaveBeenCalledWith(
      expect.stringContaining("/storyboards/42"),
      expect.objectContaining({ title: "Test Topic" }),
      expect.anything()
    );
    expect(axios.post).not.toHaveBeenCalled();
    // Verify scene IDs are updated
    expect(setScenes).toHaveBeenCalledWith([expect.objectContaining({ id: 200 })]);
  });

  it("calls POST when no storyboardId and reassigns scene IDs", async () => {
    const setContext = vi.fn();
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
        width: 512,
        height: 768,
        negative_prompt: "",
      },
    ];
    mockAllStores({ storyboardId: null, scenes, setContext, setScenes, groupId: 1 });
    (axios.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { storyboard_id: 99, scene_ids: [501] },
    });

    const result = await persistStoryboard();

    expect(result).toBe(true);
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining("/storyboards"),
      expect.objectContaining({ title: "Test Topic" }),
      expect.anything()
    );
    expect(setContext).toHaveBeenCalledWith({ storyboardId: 99, storyboardTitle: "Test Topic" });
    expect(setScenes).toHaveBeenCalledWith([expect.objectContaining({ id: 501 })]);
  });

  it("returns false on API error", async () => {
    mockAllStores({
      storyboardId: 1,
      scenes: [{ id: 0 }],
    });
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
    mockAllStores({ scenes: [], showToast });

    const result = await saveStoryboard();

    expect(result).toBe(false);
    expect(showToast).toHaveBeenCalledWith("No scenes to save", "error");
  });

  it("shows error toast when no groupId", async () => {
    const showToast = vi.fn();
    mockAllStores({ groupId: null, scenes: [{ id: 0 }], showToast });

    const result = await saveStoryboard();

    expect(result).toBe(false);
    expect(showToast).toHaveBeenCalledWith("Create a group to save your storyboard", "error");
  });

  it("shows success toast for update (existing storyboardId)", async () => {
    const showToast = vi.fn();
    mockAllStores({
      storyboardId: 42,
      scenes: [{ id: 0, script: "test" }],
      showToast,
    });
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: {} });

    const result = await saveStoryboard();

    expect(result).toBe(true);
    expect(showToast).toHaveBeenCalledWith("Storyboard updated", "success");
  });

  it("shows success toast for new save (no storyboardId)", async () => {
    const showToast = vi.fn();
    mockAllStores({
      storyboardId: null,
      scenes: [{ id: 0 }],
      groupId: 1,
      showToast,
    });
    (axios.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { storyboard_id: 10, scene_ids: [100] },
    });

    const result = await saveStoryboard();

    expect(result).toBe(true);
    expect(showToast).toHaveBeenCalledWith("Storyboard saved", "success");
  });

  it("shows error toast on failure", async () => {
    const showToast = vi.fn();
    mockAllStores({
      storyboardId: 1,
      scenes: [{ id: 0 }],
      showToast,
    });
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("fail"));

    const result = await saveStoryboard();

    expect(result).toBe(false);
    expect(showToast).toHaveBeenCalledWith("Failed to save storyboard", "error");
  });
});

describe("persistStoryboard scene index preservation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("preserves currentSceneIndex after PUT scene ID update (setScenes handles it natively)", async () => {
    const setScenes = vi.fn();
    mockAllStores({
      storyboardId: 42,
      setScenes,
      currentSceneIndex: 2, // User is viewing scene 3 (0-indexed)
      scenes: [
        { id: 100, order: 0, script: "s1" },
        { id: 101, order: 1, script: "s2" },
        { id: 102, order: 2, script: "s3" },
      ],
    });
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [200, 201, 202] },
    });

    await persistStoryboard();

    // Scene IDs should be updated
    expect(setScenes).toHaveBeenCalledWith([
      expect.objectContaining({ id: 200 }),
      expect.objectContaining({ id: 201 }),
      expect.objectContaining({ id: 202 }),
    ]);
    // setScenes now preserves currentSceneIndex natively -- no explicit restore needed
  });

  it("preserves currentSceneIndex after POST scene ID assignment (setScenes handles it natively)", async () => {
    const setScenes = vi.fn();
    const setContext = vi.fn();
    mockAllStores({
      storyboardId: null,
      setScenes,
      setContext,
      currentSceneIndex: 1, // User is viewing scene 2
      scenes: [
        { id: 0, order: 0, script: "s1" },
        { id: 1, order: 1, script: "s2" },
      ],
    });
    (axios.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { storyboard_id: 99, scene_ids: [500, 501] },
    });

    await persistStoryboard();

    expect(setScenes).toHaveBeenCalledWith([
      expect.objectContaining({ id: 500 }),
      expect.objectContaining({ id: 501 }),
    ]);
    // setScenes now preserves currentSceneIndex natively -- no explicit restore needed
  });
});

describe("sanitizeCandidatesForDb", () => {
  it("removes image_url from candidates (prevents localhost URLs in DB)", () => {
    const candidates = [
      {
        media_asset_id: 100,
        match_rate: 0.85,
        image_url: "http://localhost:9000/shorts-producer/projects/3/img.png",
      },
      {
        media_asset_id: 101,
        match_rate: 0.72,
        image_url: "http://localhost:9000/shorts-producer/projects/3/img2.png",
      },
    ];

    const result = sanitizeCandidatesForDb(candidates);

    expect(result).toEqual([
      { media_asset_id: 100, match_rate: 0.85 },
      { media_asset_id: 101, match_rate: 0.72 },
    ]);
    // Ensure image_url is NOT present
    expect(result![0]).not.toHaveProperty("image_url");
    expect(result![1]).not.toHaveProperty("image_url");
  });

  it("returns null for empty candidates array", () => {
    expect(sanitizeCandidatesForDb([])).toBeNull();
  });

  it("returns null for undefined candidates", () => {
    expect(sanitizeCandidatesForDb(undefined)).toBeNull();
  });

  it("preserves media_asset_id and match_rate only", () => {
    const candidates = [
      {
        media_asset_id: 200,
        match_rate: 0.9,
        image_url: "http://example.com/img.png",
      },
    ];

    const result = sanitizeCandidatesForDb(candidates);

    expect(result).toHaveLength(1);
    expect(Object.keys(result![0])).toEqual(["media_asset_id", "match_rate"]);
  });

  it("omits match_rate when undefined", () => {
    const candidates = [{ media_asset_id: 300, image_url: "http://example.com/img.png" }];

    const result = sanitizeCandidatesForDb(candidates);

    expect(result).toEqual([{ media_asset_id: 300 }]);
    expect(result![0]).not.toHaveProperty("match_rate");
  });

  it("handles multiple candidates with mixed match_rate presence", () => {
    const candidates = [
      { media_asset_id: 400, match_rate: 0.8, image_url: "http://a.com" },
      { media_asset_id: 401, image_url: "http://b.com" }, // no match_rate
      { media_asset_id: 402, match_rate: 0.5, image_url: "http://c.com" },
    ];

    const result = sanitizeCandidatesForDb(candidates);

    expect(result).toEqual([
      { media_asset_id: 400, match_rate: 0.8 },
      { media_asset_id: 401 },
      { media_asset_id: 402, match_rate: 0.5 },
    ]);
  });
});

describe("persistStoryboard scene ID -> image_asset_id mapping", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("preserves image_asset_id for each scene through PUT ID reassignment", async () => {
    const setScenes = vi.fn();
    const scenes = [
      { id: 3581, order: 0, script: "S1", image_asset_id: 100, image_url: "http://img1" },
      { id: 3582, order: 1, script: "S2", image_asset_id: 200, image_url: "http://img2" },
      { id: 3583, order: 2, script: "S3", image_asset_id: null, image_url: null },
    ];
    mockAllStores({
      storyboardId: 42,
      setScenes,
      scenes,
    });
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [3590, 3591, 3592] },
    });

    await persistStoryboard();

    // Verify setScenes was called with correct ID mapping
    const calledScenes = setScenes.mock.calls[0][0];
    expect(calledScenes).toHaveLength(3);
    // Scene IDs updated
    expect(calledScenes[0].id).toBe(3590);
    expect(calledScenes[1].id).toBe(3591);
    expect(calledScenes[2].id).toBe(3592);
    // image_asset_id preserved from original scenes (not shifted)
    expect(calledScenes[0].image_asset_id).toBe(100);
    expect(calledScenes[1].image_asset_id).toBe(200);
    expect(calledScenes[2].image_asset_id).toBeNull();
  });

  it("sends image_asset_id in correct array order to PUT endpoint", async () => {
    const scenes = [
      { id: 10, order: 0, script: "A", image_asset_id: 501, image_url: "http://a" },
      { id: 11, order: 1, script: "B", image_asset_id: null, image_url: null },
      { id: 12, order: 2, script: "C", image_asset_id: 502, image_url: "http://c" },
    ];
    mockAllStores({
      storyboardId: 1,
      setScenes: vi.fn(),
      scenes,
    });
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [20, 21, 22] },
    });

    await persistStoryboard();

    const payload = (axios.put as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1];
    // Verify the payload scenes are in the correct order with correct asset IDs
    expect(payload.scenes[0].image_asset_id).toBe(501);
    expect(payload.scenes[1].image_asset_id).toBeNull();
    expect(payload.scenes[2].image_asset_id).toBe(502);
  });
});
