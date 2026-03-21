import { describe, it, expect, vi, beforeEach } from "vitest";

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

function makeScene(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    client_id: `scene-${Math.random()}`,
    order: 0,
    script: "테스트 대사",
    speaker: "Narrator" as const,
    duration: 3,
    image_prompt: "",
    image_prompt_ko: "",
    image_url: null,
    negative_prompt: "",
    isGenerating: false,
    debug_payload: "",
    context_tags: { emotion: "neutral" },
    voice_design_prompt: "차분하게 읽어주세요",
    tts_asset_id: 42,
    ...overrides,
  };
}

describe("setGlobalEmotion", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    useStoryboardStore.getState().reset();
  });

  it("sets all scenes' context_tags.emotion to given value", () => {
    const scenes = [
      makeScene({ context_tags: { emotion: "neutral" } }),
      makeScene({ context_tags: { emotion: "sad" } }),
      makeScene({ context_tags: { emotion: "happy" } }),
    ];
    useStoryboardStore.getState().setScenes(scenes);
    useStoryboardStore.getState().setGlobalEmotion("excited");

    const updated = useStoryboardStore.getState().scenes;
    expect(updated.every((s) => s.context_tags?.emotion === "excited")).toBe(true);
  });

  it("clears all scenes' voice_design_prompt to null", () => {
    const scenes = [
      makeScene({ voice_design_prompt: "밝게 읽어주세요" }),
      makeScene({ voice_design_prompt: "차분하게" }),
    ];
    useStoryboardStore.getState().setScenes(scenes);
    useStoryboardStore.getState().setGlobalEmotion("tense");

    const updated = useStoryboardStore.getState().scenes;
    expect(updated.every((s) => s.voice_design_prompt === null)).toBe(true);
  });

  it("clears all scenes' tts_asset_id to null", () => {
    const scenes = [makeScene({ tts_asset_id: 100 }), makeScene({ tts_asset_id: 200 })];
    useStoryboardStore.getState().setScenes(scenes);
    useStoryboardStore.getState().setGlobalEmotion("calm");

    const updated = useStoryboardStore.getState().scenes;
    expect(updated.every((s) => s.tts_asset_id === null)).toBe(true);
  });

  it("sets isDirty to true", () => {
    const scenes = [makeScene()];
    useStoryboardStore.getState().setScenes(scenes, { fromDb: true });
    expect(useStoryboardStore.getState().isDirty).toBe(false);

    useStoryboardStore.getState().setGlobalEmotion("nostalgic");
    expect(useStoryboardStore.getState().isDirty).toBe(true);
  });

  it("preserves other context_tags fields", () => {
    const scenes = [
      makeScene({
        context_tags: {
          emotion: "neutral",
          camera: "close-up",
          mood: ["happy"],
          expression: ["smile"],
        },
      }),
    ];
    useStoryboardStore.getState().setScenes(scenes);
    useStoryboardStore.getState().setGlobalEmotion("excited");

    const tags = useStoryboardStore.getState().scenes[0].context_tags;
    expect(tags?.emotion).toBe("excited");
    expect(tags?.camera).toBe("close-up");
    expect(tags?.mood).toEqual(["happy"]);
    expect(tags?.expression).toEqual(["smile"]);
  });

  it("updates selectedEmotionPreset", () => {
    useStoryboardStore.getState().setGlobalEmotion("excited");
    expect(useStoryboardStore.getState().selectedEmotionPreset).toBe("excited");
  });

  it("handles scenes without context_tags", () => {
    const scenes = [makeScene({ context_tags: undefined })];
    useStoryboardStore.getState().setScenes(scenes);
    useStoryboardStore.getState().setGlobalEmotion("tense");

    const updated = useStoryboardStore.getState().scenes;
    expect(updated[0].context_tags?.emotion).toBe("tense");
  });
});
