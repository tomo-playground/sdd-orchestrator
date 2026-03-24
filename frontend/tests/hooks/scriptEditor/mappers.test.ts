// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { Scene } from "../../../app/types";

// Mock external stores before importing mappers
vi.mock("../../../app/store/useStoryboardStore", () => {
  const setScenes = vi.fn();
  const set = vi.fn();
  return {
    useStoryboardStore: Object.assign(vi.fn(), {
      getState: () => ({ setScenes, set }),
    }),
    __mockSetScenes: setScenes,
    __mockSet: set,
  };
});
vi.mock("../../../app/utils/uuid", () => ({
  generateSceneClientId: () => "test-client-id",
}));

import { mapEventScenes, mapLoadedScenes, syncToGlobalStore } from "../../../app/hooks/scriptEditor/mappers";
import { useStoryboardStore } from "../../../app/store/useStoryboardStore";

describe("mapEventScenes", () => {
  it("maps Scene[] to SceneItem[] with defaults", () => {
    const scenes: Scene[] = [
      {
        id: 10,
        client_id: "c1",
        order: 1,
        script: "Hello",
        speaker: "A",
        duration: 5,
        image_prompt: "prompt",
        image_prompt_ko: "프롬프트",
        image_url: "http://img.png",
        negative_prompt: "bad",
        isGenerating: false,
        debug_payload: "",
      },
    ];
    const result = mapEventScenes(scenes);
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe(10);
    expect(result[0].client_id).toBe("test-client-id");
    expect(result[0].script).toBe("Hello");
    expect(result[0].speaker).toBe("A");
    expect(result[0].duration).toBe(5);
    expect(result[0].image_url).toBe("http://img.png");
  });

  it("fills null/undefined fields with defaults", () => {
    const scenes = [{ id: 0 }] as unknown as Scene[];
    const result = mapEventScenes(scenes);
    expect(result[0].script).toBe("");
    expect(result[0].speaker).toBe("Narrator");
    expect(result[0].duration).toBe(3);
    expect(result[0].image_prompt).toBe("");
    expect(result[0].image_url).toBeNull();
    expect(result[0].order).toBe(1);
  });

  it("maps background_id", () => {
    const scenes = [
      { id: 1, background_id: 42 },
    ] as unknown as Scene[];
    const result = mapEventScenes(scenes);
    expect(result[0].background_id).toBe(42);
  });

  it("maps optional per-scene settings", () => {
    const scenes = [
      {
        id: 1,
        use_controlnet: true,
        controlnet_weight: 0.5,
        ken_burns_preset: "slow_zoom",
      },
    ] as unknown as Scene[];
    const result = mapEventScenes(scenes);
    expect(result[0].use_controlnet).toBe(true);
    expect(result[0].controlnet_weight).toBe(0.5);
    expect(result[0].ken_burns_preset).toBe("slow_zoom");
  });
});

describe("mapLoadedScenes", () => {
  it("preserves existing client_id from loaded data", () => {
    const scenes = [
      { id: 1, client_id: "existing-id", script: "Hello" },
    ] as unknown as Scene[];
    const result = mapLoadedScenes(scenes);
    expect(result[0].client_id).toBe("existing-id");
  });

  it("generates client_id when not present", () => {
    const scenes = [{ id: 1, script: "Hello" }] as unknown as Scene[];
    const result = mapLoadedScenes(scenes);
    expect(result[0].client_id).toBe("test-client-id");
  });

  it("shares same field mapping as mapEventScenes", () => {
    const scene = {
      id: 5,
      order: 2,
      script: "Test",
      speaker: "Bob",
      duration: 7,
      image_prompt: "img",
      ken_burns_preset: "slow_zoom",
      background_id: 42,
    } as unknown as Scene;
    const loaded = mapLoadedScenes([scene]);
    const event = mapEventScenes([scene]);
    // All fields except client_id should match
    const { client_id: _a, ...loadedRest } = loaded[0];
    const { client_id: _b, ...eventRest } = event[0];
    expect(loadedRest).toEqual(eventRest);
  });
});

describe("syncToGlobalStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls setScenes and set on storyboard store", () => {
    const scenes = [
      {
        id: 1,
        client_id: "c1",
        order: 1,
        script: "Hi",
        speaker: "Narrator",
        duration: 3,
        image_prompt: "",
        image_prompt_ko: "",
        image_url: null,
      },
    ];
    syncToGlobalStore(scenes, {
      topic: "Test",
      description: "Desc",
      duration: 30,
      language: "korean",
      structure: "monologue",
      characterId: 5,
      characterName: "Alice",
    });

    const store = useStoryboardStore.getState();
    expect(store.setScenes).toHaveBeenCalledTimes(1);
    expect(store.set).toHaveBeenCalledWith(
      expect.objectContaining({
        topic: "Test",
        selectedCharacterId: 5,
        selectedCharacterName: "Alice",
      })
    );
  });

  it("defaults null for missing character fields", () => {
    syncToGlobalStore([], {
      topic: "",
      description: "",
      duration: 30,
      language: "korean",
      structure: "monologue",
    });

    const store = useStoryboardStore.getState();
    expect(store.set).toHaveBeenCalledWith(
      expect.objectContaining({
        selectedCharacterId: null,
        selectedCharacterName: null,
        selectedCharacterBId: null,
        selectedCharacterBName: null,
      })
    );
  });
});
