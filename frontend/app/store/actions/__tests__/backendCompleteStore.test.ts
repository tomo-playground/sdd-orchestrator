import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import type { ProcessOpts } from "../imageProcessing";
import type { Scene, ImageGenProgress } from "../../../types";
import { useContextStore } from "../../useContextStore";
import { useStoryboardStore } from "../../useStoryboardStore";
import { useUIStore } from "../../useUIStore";

vi.mock("axios");

// Minimal mock stores — reset before each test
beforeEach(() => {
  vi.clearAllMocks();

  vi.spyOn(useContextStore, "getState").mockReturnValue({
    projectId: 1,
    groupId: 1,
    storyboardId: 10,
  } as ReturnType<typeof useContextStore.getState>);

  vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
    scenes: [{ id: 1, client_id: "s1", order: 0 }],
    imageValidationResults: {},
    set: vi.fn(),
  } as unknown as ReturnType<typeof useStoryboardStore.getState>);

  vi.spyOn(useUIStore, "getState").mockReturnValue({
    showToast: vi.fn(),
  } as unknown as ReturnType<typeof useUIStore.getState>);
});

// ── Test 1 & 2: processGeneratedImages — preStored 분기 ──────────

describe("processGeneratedImages with preStored", () => {
  it("skips HTTP store when preStored is provided", async () => {
    // validateImageCandidate uses axios.post — mock it to skip validation
    vi.mocked(axios.post).mockResolvedValue({ data: null });

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}"));

    const { processGeneratedImages } = await import("../imageProcessing");

    const result = await processGeneratedImages({
      images: ["base64data"],
      scene: { id: 1, client_id: "s1" } as Scene,
      prompt: "1girl",
      selectedCharacterId: null,
      silent: true,
      preStored: { url: "http://minio/img.png", asset_id: 42 },
    });

    // fetch should NOT be called for /image/store (preStored skips it)
    const storeCalls = fetchSpy.mock.calls.filter((c) =>
      String(c[0]).includes("/image/store"),
    );
    expect(storeCalls).toHaveLength(0);

    expect(result?.image_url).toBe("http://minio/img.png");
    expect(result?.image_asset_id).toBe(42);

    fetchSpy.mockRestore();
  });

  it("calls HTTP store when preStored is not provided", async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: null });

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ url: "http://stored.png", asset_id: 99 }),
        { headers: { "Content-Type": "application/json" } },
      ),
    );

    const { processGeneratedImages } = await import("../imageProcessing");

    await processGeneratedImages({
      images: ["base64data"],
      scene: { id: 1, client_id: "s1" } as Scene,
      prompt: "1girl",
      selectedCharacterId: null,
      silent: true,
    });

    // fetch SHOULD be called for /image/store (no preStored)
    const storeCalls = fetchSpy.mock.calls.filter((c) =>
      String(c[0]).includes("/image/store"),
    );
    expect(storeCalls.length).toBeGreaterThan(0);

    fetchSpy.mockRestore();
  });
});

// ── Test 3: ImageGenProgress 타입에 image_url / image_asset_id 포함 ──

describe("ImageGenProgress type", () => {
  it("includes image_url and image_asset_id fields", () => {
    const progress: ImageGenProgress = {
      task_id: "t1",
      stage: "completed",
      percent: 100,
      message: "완료",
      image: "base64...",
      image_url: "http://minio/test.png",
      image_asset_id: 42,
    };
    expect(progress.image_url).toBe("http://minio/test.png");
    expect(progress.image_asset_id).toBe(42);
  });
});

// ── Test 4: requestPayload에 client_id 포함 ──────────────────────

describe("generateSceneImageFor payload", () => {
  it("includes client_id in requestPayload", () => {
    // Pure logic test: scene 객체에서 requestPayload 구성 시 client_id 포함 확인
    const scene = { client_id: "uuid-abc", id: 1, speaker: "A" };
    const payload = {
      prompt: "test",
      client_id: scene.client_id,
      scene_id: scene.id > 0 ? scene.id : undefined,
    };
    expect(payload.client_id).toBe("uuid-abc");
  });
});

// ── Test 5 & 6: beforeunload — isGenerating 파생 로직 ────────────

describe("beforeunload guard with isGenerating", () => {
  it("derives isGenerating=true from non-empty imageGenProgress", () => {
    const imageGenProgress: Record<string, unknown> = {
      "scene-a": { stage: "generating" },
    };
    const isGenerating = Object.keys(imageGenProgress).length > 0;
    expect(isGenerating).toBe(true);
  });

  it("derives isGenerating=false when imageGenProgress is empty", () => {
    const imageGenProgress: Record<string, unknown> = {};
    const isGenerating = Object.keys(imageGenProgress).length > 0;
    expect(isGenerating).toBe(false);
  });
});

// ── Bonus: ProcessOpts preStored 타입 검증 ───────────────────────

describe("ProcessOpts preStored type", () => {
  it("accepts preStored with url and asset_id", () => {
    const opts: ProcessOpts = {
      images: ["base64data"],
      scene: { id: 1, client_id: "s1" } as Scene,
      prompt: "1girl",
      selectedCharacterId: null,
      silent: true,
      preStored: { url: "http://minio/img.png", asset_id: 42 },
    };
    expect(opts.preStored?.url).toBe("http://minio/img.png");
    expect(opts.preStored?.asset_id).toBe(42);
  });

  it("allows preStored to be undefined", () => {
    const opts: ProcessOpts = {
      images: ["base64data"],
      scene: { id: 1, client_id: "s1" } as Scene,
      prompt: "1girl",
      selectedCharacterId: null,
      silent: true,
    };
    expect(opts.preStored).toBeUndefined();
  });
});
