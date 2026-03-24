import { describe, it, expect, vi, beforeEach } from "vitest";

// Zustand v5 createJSONStorage captures localStorage at module load time.
// vi.hoisted() runs before ESM imports, ensuring our mock is captured.
const localStorageMock = vi.hoisted(() => {
  const store: Record<string, string> = {};
  const mock = {
    store,
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      for (const k of Object.keys(store)) delete store[k];
    },
    key: () => null,
    length: 0,
  };
  globalThis.localStorage = mock as unknown as Storage;
  return mock;
});

import { useStoryboardStore } from "../useStoryboardStore";

/**
 * updateScene의 isDirty 분리 검증.
 * transient 필드(isGenerating 등)만 변경 시 isDirty가 설정되지 않아야 함.
 * 이를 통해 이미지 생성 중 autoSave가 stale 데이터로 덮어쓰는 race condition 방지.
 */
describe("updateScene isDirty — transient vs persistable fields", () => {
  const CLIENT_ID = "test-client-id";

  beforeEach(() => {
    localStorageMock.store = {};
    useStoryboardStore.getState().reset();
    useStoryboardStore.getState().setScenes([
      {
        id: 1,
        client_id: CLIENT_ID,
        order: 0,
        script: "test script",
        speaker: "narrator",
        duration: 3,
        image_prompt: "1girl",
        image_prompt_ko: "",
        image_url: null,
        width: 832,
        height: 1216,
        negative_prompt: "",
        isGenerating: false,
        debug_payload: "",
      },
    ]);
    // setScenes sets isDirty: true, clear it
    useStoryboardStore.getState().set({ isDirty: false });
  });

  it("isGenerating만 변경 시 isDirty 미설정", () => {
    useStoryboardStore.getState().updateScene(CLIENT_ID, { isGenerating: true });
    expect(useStoryboardStore.getState().isDirty).toBe(false);
  });

  it("debug_payload만 변경 시 isDirty 미설정", () => {
    useStoryboardStore.getState().updateScene(CLIENT_ID, { debug_payload: '{"test":true}' });
    expect(useStoryboardStore.getState().isDirty).toBe(false);
  });

  it("debug_prompt만 변경 시 isDirty 미설정", () => {
    useStoryboardStore.getState().updateScene(CLIENT_ID, { debug_prompt: "test prompt" });
    expect(useStoryboardStore.getState().isDirty).toBe(false);
  });

  it("_auto_pin_previous만 변경 시 isDirty 미설정", () => {
    useStoryboardStore.getState().updateScene(CLIENT_ID, { _auto_pin_previous: true });
    expect(useStoryboardStore.getState().isDirty).toBe(false);
  });

  it("여러 transient 필드 동시 변경 시 isDirty 미설정", () => {
    useStoryboardStore.getState().updateScene(CLIENT_ID, {
      isGenerating: true,
      debug_payload: '{"steps":27}',
      debug_prompt: "composed prompt",
    });
    expect(useStoryboardStore.getState().isDirty).toBe(false);
  });

  it("script 변경 시 isDirty 설정", () => {
    useStoryboardStore.getState().updateScene(CLIENT_ID, { script: "new script" });
    expect(useStoryboardStore.getState().isDirty).toBe(true);
  });

  it("image_asset_id 변경 시 isDirty 설정", () => {
    useStoryboardStore.getState().updateScene(CLIENT_ID, { image_asset_id: 100 });
    expect(useStoryboardStore.getState().isDirty).toBe(true);
  });

  it("image_url 변경 시 isDirty 설정", () => {
    useStoryboardStore
      .getState()
      .updateScene(CLIENT_ID, { image_url: "http://example.com/img.png" });
    expect(useStoryboardStore.getState().isDirty).toBe(true);
  });

  it("candidates 변경 시 isDirty 설정", () => {
    useStoryboardStore.getState().updateScene(CLIENT_ID, {
      candidates: [{ media_asset_id: 1 }],
    });
    expect(useStoryboardStore.getState().isDirty).toBe(true);
  });

  it("persistable + transient 혼합 시 isDirty 설정 (이미지 생성 완료 패턴)", () => {
    useStoryboardStore.getState().updateScene(CLIENT_ID, {
      image_url: "http://example.com/img.png",
      image_asset_id: 100,
      isGenerating: false,
    });
    expect(useStoryboardStore.getState().isDirty).toBe(true);
  });

  it("transient 필드 변경 후에도 씬 데이터는 정상 업데이트", () => {
    useStoryboardStore.getState().updateScene(CLIENT_ID, { isGenerating: true });
    const scene = useStoryboardStore.getState().scenes[0];
    expect(scene.isGenerating).toBe(true);
    expect(scene.script).toBe("test script"); // 기존 데이터 보존
  });
});
