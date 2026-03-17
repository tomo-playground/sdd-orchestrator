import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { persistStoryboard, saveStoryboard, sanitizeCandidatesForDb } from "../storyboardActions";
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
    const { sbState } = mockAllStores({
      storyboardId: 42,
      scenes: [
        {
          id: 100, // Old scene ID
          script: "test",
          speaker: "Narrator",
          duration: 3,
          image_prompt: "prompt",
          image_prompt_ko: "",
          image_url: null,
          width: 832,
          height: 1216,
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
    // Verify atomic set() with updated scene IDs + isDirty: false
    expect(sbState.set).toHaveBeenCalledWith(
      expect.objectContaining({
        scenes: [expect.objectContaining({ id: 200 })],
        isDirty: false,
      })
    );
  });

  it("calls POST when no storyboardId and reassigns scene IDs", async () => {
    const setContext = vi.fn();
    const scenes = [
      {
        id: 0,
        script: "test",
        speaker: "Narrator",
        duration: 3,
        image_prompt: "",
        image_prompt_ko: "",
        image_url: null,
        width: 832,
        height: 1216,
        negative_prompt: "",
      },
    ];
    const { sbState } = mockAllStores({ storyboardId: null, scenes, setContext, groupId: 1 });
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
    // Verify atomic set() with updated scene IDs + isDirty: false
    expect(sbState.set).toHaveBeenCalledWith(
      expect.objectContaining({
        scenes: [expect.objectContaining({ id: 501 })],
        isDirty: false,
      })
    );
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
    expect(showToast).toHaveBeenCalledWith("저장할 씬이 없습니다", "error");
  });

  it("shows error toast when no groupId", async () => {
    const showToast = vi.fn();
    mockAllStores({ groupId: null, scenes: [{ id: 0 }], showToast });

    const result = await saveStoryboard();

    expect(result).toBe(false);
    expect(showToast).toHaveBeenCalledWith("영상을 저장하려면 시리즈를 생성하세요", "error");
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
    expect(showToast).toHaveBeenCalledWith("영상 저장 완료", "success");
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
    expect(showToast).toHaveBeenCalledWith("영상 저장 완료", "success");
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
    expect(showToast).toHaveBeenCalledWith("영상 저장에 실패했습니다", "error");
  });
});

describe("persistStoryboard scene index preservation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("preserves currentSceneIndex after PUT scene ID update (atomic set preserves it)", async () => {
    const { sbState } = mockAllStores({
      storyboardId: 42,
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

    // Atomic set() updates scenes + isDirty without touching currentSceneIndex
    expect(sbState.set).toHaveBeenCalledWith(
      expect.objectContaining({
        scenes: [
          expect.objectContaining({ id: 200 }),
          expect.objectContaining({ id: 201 }),
          expect.objectContaining({ id: 202 }),
        ],
        isDirty: false,
      })
    );
  });

  it("preserves currentSceneIndex after POST scene ID assignment (atomic set preserves it)", async () => {
    const setContext = vi.fn();
    const { sbState } = mockAllStores({
      storyboardId: null,
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

    expect(sbState.set).toHaveBeenCalledWith(
      expect.objectContaining({
        scenes: [expect.objectContaining({ id: 500 }), expect.objectContaining({ id: 501 })],
        isDirty: false,
      })
    );
  });
});

describe("didScenesChangeDuringSave — deep comparison for objects", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("same context_tags content but different reference → isDirty: false", async () => {
    const tags = { pose: "standing", expression: "smile", environment: ["office"] };
    const scenesBeforeSave = [
      {
        id: 1,
        client_id: "c1",
        script: "S1",
        image_asset_id: 100,
        image_url: null,
        context_tags: { ...tags },
      },
    ];
    // Different object reference but same content
    const scenesAfterSave = [
      {
        id: 1,
        client_id: "c1",
        script: "S1",
        image_asset_id: 100,
        image_url: null,
        context_tags: { ...tags },
      },
    ];

    const getStateSpy = vi.spyOn(useStoryboardStore, "getState");
    const sbBase = makeStoryboardState({ scenes: scenesBeforeSave });
    const sbAfter = makeStoryboardState({ scenes: scenesAfterSave });

    getStateSpy
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbAfter as never)
      .mockReturnValueOnce(sbAfter as never);

    vi.spyOn(useContextStore, "getState").mockReturnValue(
      makeContextState({ storyboardId: 42, groupId: 1 }) as never
    );
    vi.spyOn(useUIStore, "getState").mockReturnValue(makeUIState() as never);
    vi.spyOn(useRenderStore, "getState").mockReturnValue(makeRenderState() as never);

    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [10], version: 2 },
    });

    await persistStoryboard();

    expect(sbAfter.set).toHaveBeenCalledWith(expect.objectContaining({ isDirty: false }));
  });

  it("same candidates content but different reference → isDirty: false", async () => {
    const cands = [{ media_asset_id: 100, match_rate: 0.8 }];
    const scenesBeforeSave = [
      {
        id: 1,
        client_id: "c1",
        script: "S1",
        image_asset_id: 100,
        image_url: null,
        candidates: [...cands],
      },
    ];
    const scenesAfterSave = [
      {
        id: 1,
        client_id: "c1",
        script: "S1",
        image_asset_id: 100,
        image_url: null,
        candidates: [...cands],
      },
    ];

    const getStateSpy = vi.spyOn(useStoryboardStore, "getState");
    const sbBase = makeStoryboardState({ scenes: scenesBeforeSave });
    const sbAfter = makeStoryboardState({ scenes: scenesAfterSave });

    getStateSpy
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbAfter as never)
      .mockReturnValueOnce(sbAfter as never);

    vi.spyOn(useContextStore, "getState").mockReturnValue(
      makeContextState({ storyboardId: 42, groupId: 1 }) as never
    );
    vi.spyOn(useUIStore, "getState").mockReturnValue(makeUIState() as never);
    vi.spyOn(useRenderStore, "getState").mockReturnValue(makeRenderState() as never);

    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [10], version: 2 },
    });

    await persistStoryboard();

    expect(sbAfter.set).toHaveBeenCalledWith(expect.objectContaining({ isDirty: false }));
  });

  it("actually different context_tags content → isDirty: true", async () => {
    const scenesBeforeSave = [
      {
        id: 1,
        client_id: "c1",
        script: "S1",
        image_asset_id: 100,
        image_url: null,
        context_tags: { pose: "standing" },
      },
    ];
    const scenesAfterSave = [
      {
        id: 1,
        client_id: "c1",
        script: "S1",
        image_asset_id: 100,
        image_url: null,
        context_tags: { pose: "sitting" },
      },
    ];

    const getStateSpy = vi.spyOn(useStoryboardStore, "getState");
    const sbBase = makeStoryboardState({ scenes: scenesBeforeSave });
    const sbAfter = makeStoryboardState({ scenes: scenesAfterSave });

    getStateSpy
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbAfter as never)
      .mockReturnValueOnce(sbAfter as never);

    vi.spyOn(useContextStore, "getState").mockReturnValue(
      makeContextState({ storyboardId: 42, groupId: 1 }) as never
    );
    vi.spyOn(useUIStore, "getState").mockReturnValue(makeUIState() as never);
    vi.spyOn(useRenderStore, "getState").mockReturnValue(makeRenderState() as never);

    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [10], version: 2 },
    });

    await persistStoryboard();

    expect(sbAfter.set).toHaveBeenCalledWith(expect.objectContaining({ isDirty: true }));
  });

  it("same array reference → isDirty: false (fast path)", async () => {
    const scenes = [{ id: 1, client_id: "c1", script: "S1", image_asset_id: 100, image_url: null }];
    // Same reference for both before and after
    const sbState = makeStoryboardState({ scenes });

    const getStateSpy = vi.spyOn(useStoryboardStore, "getState");
    getStateSpy.mockReturnValue(sbState as never);

    vi.spyOn(useContextStore, "getState").mockReturnValue(
      makeContextState({ storyboardId: 42, groupId: 1 }) as never
    );
    vi.spyOn(useUIStore, "getState").mockReturnValue(makeUIState() as never);
    vi.spyOn(useRenderStore, "getState").mockReturnValue(makeRenderState() as never);

    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [10], version: 2 },
    });

    await persistStoryboard();

    expect(sbState.set).toHaveBeenCalledWith(expect.objectContaining({ isDirty: false }));
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
    const scenes = [
      { id: 3581, order: 0, script: "S1", image_asset_id: 100, image_url: "http://img1" },
      { id: 3582, order: 1, script: "S2", image_asset_id: 200, image_url: "http://img2" },
      { id: 3583, order: 2, script: "S3", image_asset_id: null, image_url: null },
    ];
    const { sbState } = mockAllStores({
      storyboardId: 42,
      scenes,
    });
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [3590, 3591, 3592] },
    });

    await persistStoryboard();

    // Verify atomic set() was called with correct ID mapping
    const setCall = sbState.set.mock.calls.find(
      (call: unknown[]) => (call[0] as Record<string, unknown>).scenes !== undefined
    );
    expect(setCall).toBeDefined();
    const calledScenes = (setCall![0] as Record<string, unknown>).scenes as Record<
      string,
      unknown
    >[];
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

describe("persistStoryboard — save 중 변경 감지 (isDirty 유지)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("save 중 씬 변경 없으면 isDirty: false", async () => {
    const scenes = [
      { id: 1, client_id: "c1", script: "S1", image_asset_id: 100, image_url: "http://img1" },
    ];
    const { sbState } = mockAllStores({ storyboardId: 42, scenes });
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [10], version: 2 },
    });

    await persistStoryboard();

    expect(sbState.set).toHaveBeenCalledWith(expect.objectContaining({ isDirty: false }));
  });

  it("save 중 image_asset_id 변경 시 isDirty: true 유지 (race condition 방어)", async () => {
    const scenesBeforeSave = [
      { id: 1, client_id: "c1", script: "S1", image_asset_id: null, image_url: null },
    ];
    const scenesAfterSave = [
      { id: 1, client_id: "c1", script: "S1", image_asset_id: 100, image_url: "http://new-img" },
    ];

    // getState() 호출 순서:
    // 1) scenes.length check  2) sbState destructure
    // 3) scenesAfterSave read 4) .set() 호출
    const getStateSpy = vi.spyOn(useStoryboardStore, "getState");
    const sbBase = makeStoryboardState({ scenes: scenesBeforeSave });
    const sbAfter = makeStoryboardState({ scenes: scenesAfterSave });

    getStateSpy
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbAfter as never)
      .mockReturnValueOnce(sbAfter as never);

    vi.spyOn(useContextStore, "getState").mockReturnValue(
      makeContextState({ storyboardId: 42, groupId: 1 }) as never
    );
    vi.spyOn(useUIStore, "getState").mockReturnValue(makeUIState() as never);
    vi.spyOn(useRenderStore, "getState").mockReturnValue(makeRenderState() as never);

    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [10], version: 2 },
    });

    await persistStoryboard();

    expect(sbAfter.set).toHaveBeenCalledWith(expect.objectContaining({ isDirty: true }));
  });

  it("save 중 script 변경 시 isDirty: true 유지", async () => {
    const scenesBeforeSave = [
      { id: 1, client_id: "c1", script: "Original", image_asset_id: null, image_url: null },
    ];
    const scenesAfterSave = [
      {
        id: 1,
        client_id: "c1",
        script: "Edited during save",
        image_asset_id: null,
        image_url: null,
      },
    ];

    const getStateSpy = vi.spyOn(useStoryboardStore, "getState");
    const sbBase = makeStoryboardState({ scenes: scenesBeforeSave });
    const sbAfter = makeStoryboardState({ scenes: scenesAfterSave });

    getStateSpy
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbAfter as never)
      .mockReturnValueOnce(sbAfter as never);

    vi.spyOn(useContextStore, "getState").mockReturnValue(
      makeContextState({ storyboardId: 42, groupId: 1 }) as never
    );
    vi.spyOn(useUIStore, "getState").mockReturnValue(makeUIState() as never);
    vi.spyOn(useRenderStore, "getState").mockReturnValue(makeRenderState() as never);

    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [10], version: 2 },
    });

    await persistStoryboard();

    expect(sbAfter.set).toHaveBeenCalledWith(expect.objectContaining({ isDirty: true }));
  });

  it("save 중 씬 개수 변경 시 isDirty: true 유지", async () => {
    const scenesBeforeSave = [
      { id: 1, client_id: "c1", script: "S1", image_asset_id: null, image_url: null },
    ];
    const scenesAfterSave = [
      { id: 1, client_id: "c1", script: "S1", image_asset_id: null, image_url: null },
      { id: 0, client_id: "c2", script: "S2", image_asset_id: null, image_url: null },
    ];

    const getStateSpy = vi.spyOn(useStoryboardStore, "getState");
    const sbBase = makeStoryboardState({ scenes: scenesBeforeSave });
    const sbAfter = makeStoryboardState({ scenes: scenesAfterSave });

    getStateSpy
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbAfter as never)
      .mockReturnValueOnce(sbAfter as never);

    vi.spyOn(useContextStore, "getState").mockReturnValue(
      makeContextState({ storyboardId: 42, groupId: 1 }) as never
    );
    vi.spyOn(useUIStore, "getState").mockReturnValue(makeUIState() as never);
    vi.spyOn(useRenderStore, "getState").mockReturnValue(makeRenderState() as never);

    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { scene_ids: [10], version: 2 },
    });

    await persistStoryboard();

    expect(sbAfter.set).toHaveBeenCalledWith(expect.objectContaining({ isDirty: true }));
  });

  it("POST (신규 저장) 시에도 save 중 변경 감지 동작", async () => {
    const scenesBeforeSave = [
      { id: 0, client_id: "c1", script: "S1", image_asset_id: null, image_url: null },
    ];
    const scenesAfterSave = [
      { id: 0, client_id: "c1", script: "S1", image_asset_id: 200, image_url: "http://new" },
    ];

    const getStateSpy = vi.spyOn(useStoryboardStore, "getState");
    const sbBase = makeStoryboardState({ scenes: scenesBeforeSave });
    const sbAfter = makeStoryboardState({ scenes: scenesAfterSave });

    getStateSpy
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbBase as never)
      .mockReturnValueOnce(sbAfter as never)
      .mockReturnValueOnce(sbAfter as never);

    vi.spyOn(useContextStore, "getState").mockReturnValue(
      makeContextState({ storyboardId: null, groupId: 1 }) as never
    );
    vi.spyOn(useUIStore, "getState").mockReturnValue(makeUIState() as never);
    vi.spyOn(useRenderStore, "getState").mockReturnValue(makeRenderState() as never);

    (axios.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { storyboard_id: 99, scene_ids: [500], version: 1 },
    });

    await persistStoryboard();

    expect(sbAfter.set).toHaveBeenCalledWith(expect.objectContaining({ isDirty: true }));
  });
});
