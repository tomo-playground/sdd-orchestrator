import { describe, expect, test } from "vitest";
import { buildScenesPayload } from "../buildScenesPayload";
import type { Scene } from "../../types";

/** Minimal Scene factory for testing */
function makeScene(overrides: Partial<Scene> = {}): Scene {
  return {
    id: 1,
    client_id: "test-client-1",
    order: 0,
    script: "test script",
    speaker: "narrator",
    duration: 3,
    scene_mode: "single" as const,
    image_prompt: "test prompt",
    image_prompt_ko: "",
    negative_prompt: "",
    width: 832,
    height: 1216,
    isGenerating: false,
    ...overrides,
  } as Scene;
}

describe("buildScenesPayload asset preservation", () => {
  test("image_asset_id가 payload에 포함되어야 한다", () => {
    const scene = makeScene({ image_asset_id: 8160 });
    const payload = buildScenesPayload([scene]);
    expect(payload[0].image_asset_id).toBe(8160);
  });

  test("tts_asset_id가 payload에 포함되어야 한다", () => {
    const scene = makeScene({ tts_asset_id: 42 });
    const payload = buildScenesPayload([scene]);
    expect(payload[0].tts_asset_id).toBe(42);
  });

  test("image_asset_id가 null이면 null로 전달", () => {
    const scene = makeScene({ image_asset_id: null });
    const payload = buildScenesPayload([scene]);
    expect(payload[0].image_asset_id).toBeNull();
  });

  test("image_asset_id가 undefined이면 필드 자체가 없어도 OK (optional)", () => {
    const scene = makeScene();
    // image_asset_id not set → undefined in spread
    const payload = buildScenesPayload([scene]);
    // Should not throw; field is optional
    expect(payload[0]).toBeDefined();
  });

  test("image_url은 제외되어야 한다 (DB 직접 저장 금지)", () => {
    const scene = makeScene({ image_url: "http://example.com/img.png" } as Partial<Scene>);
    const payload = buildScenesPayload([scene]);
    expect(payload[0]).not.toHaveProperty("image_url");
  });

  test("UI-only 필드는 제외되어야 한다", () => {
    const scene = makeScene({
      isGenerating: true,
      debug_payload: "debug",
      debug_prompt: "prompt",
    });
    const payload = buildScenesPayload([scene]);
    expect(payload[0]).not.toHaveProperty("isGenerating");
    expect(payload[0]).not.toHaveProperty("debug_payload");
    expect(payload[0]).not.toHaveProperty("debug_prompt");
  });
});
