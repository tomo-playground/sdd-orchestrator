import { describe, it, expect } from "vitest";
import { checkTtsStep } from "../preflight-steps";
import type { Scene, DraftScene } from "../../types";

// ── helpers ────────────────────────────────────────────────

function makeScene(overrides: Partial<Scene> = {}): Scene {
  return {
    id: 1,
    client_id: "scene-1",
    order: 0,
    script: "테스트 스크립트",
    speaker: "Narrator",
    duration: 3,
    image_prompt: "",
    image_prompt_ko: "",
    image_url: null,
    negative_prompt: "",
    isGenerating: false,
    debug_payload: "",
    ...overrides,
  } as Scene;
}

// ── checkTtsStep ───────────────────────────────────────────

describe("checkTtsStep", () => {
  it("빈 씬 배열 → valid: false, value: 스크립트 없음", () => {
    const result = checkTtsStep([]);
    expect(result.valid).toBe(false);
    expect(result.value).toBe("스크립트 없음");
    expect(result.required).toBe(false);
  });

  it("스크립트 없는 씬들만 있을 때 → valid: false, value: 스크립트 없음", () => {
    const scenes = [
      makeScene({ script: "" }),
      makeScene({ script: "   " }),
      makeScene({ script: undefined as unknown as string }),
    ];
    const result = checkTtsStep(scenes);
    expect(result.valid).toBe(false);
    expect(result.value).toBe("스크립트 없음");
    expect(result.required).toBe(false);
  });

  it("모든 씬에 tts_asset_id 있음 → valid: false, value: All prebuilt (스텝 스킵)", () => {
    const scenes = [
      makeScene({ script: "씬 1", tts_asset_id: 10 }),
      makeScene({ script: "씬 2", tts_asset_id: 20 }),
      makeScene({ script: "씬 3", tts_asset_id: 30 }),
    ];
    const result = checkTtsStep(scenes);
    expect(result.valid).toBe(false);
    expect(result.value).toBe("All prebuilt");
    expect(result.required).toBe(false);
  });

  it("일부 씬에 tts_asset_id 없음 → valid: true, value: N개 생성 필요 (스텝 실행)", () => {
    const scenes = [
      makeScene({ script: "씬 1", tts_asset_id: 10 }),
      makeScene({ script: "씬 2", tts_asset_id: null }),
      makeScene({ script: "씬 3", tts_asset_id: undefined }),
    ];
    const result = checkTtsStep(scenes);
    expect(result.valid).toBe(true);
    expect(result.value).toBe("2개 생성 필요");
    expect(result.required).toBe(false);
  });

  it("모든 씬에 tts_asset_id 없음 → valid: true, 전체 개수 반환", () => {
    const scenes = [
      makeScene({ script: "씬 1" }),
      makeScene({ script: "씬 2" }),
      makeScene({ script: "씬 3" }),
    ];
    const result = checkTtsStep(scenes);
    expect(result.valid).toBe(true);
    expect(result.value).toBe("3개 생성 필요");
  });

  it("스크립트 없는 씬은 카운트에서 제외 (script?.trim() 기준)", () => {
    const scenes = [
      makeScene({ script: "", tts_asset_id: null }),       // 스크립트 없음 → 무시
      makeScene({ script: "  ", tts_asset_id: null }),     // 공백만 → 무시
      makeScene({ script: "실제 스크립트", tts_asset_id: null }), // 생성 필요
    ];
    const result = checkTtsStep(scenes);
    expect(result.valid).toBe(true);
    expect(result.value).toBe("1개 생성 필요");
  });

  it("스크립트 없는 씬 제외 후 나머지가 모두 prebuilt → valid: false", () => {
    const scenes = [
      makeScene({ script: "", tts_asset_id: null }),       // 스크립트 없음 → 무시
      makeScene({ script: "씬 A", tts_asset_id: 99 }),     // prebuilt
    ];
    const result = checkTtsStep(scenes);
    expect(result.valid).toBe(false);
    expect(result.value).toBe("All prebuilt");
  });

  it("DraftScene 타입도 처리 (tts_asset_id 없음 → 생성 필요)", () => {
    const draft: DraftScene = {
      client_id: "draft-1",
      order: 0,
      script: "드래프트 씬",
      speaker: "Narrator",
      duration: 3,
      image_prompt: "",
      image_prompt_ko: "",
      image_url: null,
      negative_prompt: "",
      isGenerating: false,
      debug_payload: "",
    } as DraftScene;
    const result = checkTtsStep([draft]);
    expect(result.valid).toBe(true);
    expect(result.value).toBe("1개 생성 필요");
  });
});
