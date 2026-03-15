import { describe, it, expect, vi, beforeEach } from "vitest";

// Zustand v5 persist requires localStorage mock before import
vi.hoisted(() => {
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
});

import {
  buildSyncMeta,
  buildGenerateBody,
  buildSavePayload,
  handleStreamOutcome,
} from "../../../app/hooks/scriptEditor/actions";
import type { ScriptEditorState, SceneItem } from "../../../app/hooks/scriptEditor/types";

function makeEditorState(overrides: Partial<ScriptEditorState> = {}): ScriptEditorState {
  return {
    topic: "Test Topic",
    description: "Test description",
    duration: 60,
    language: "ko",
    structure: "Monologue",
    characterId: 1,
    characterName: "Alice",
    characterBId: null,
    characterBName: null,
    scenes: [],
    isGenerating: false,
    progress: null,
    storyboardId: null,
    storyboardVersion: null,
    isSaving: false,
    directorSkipStages: [],
    threadId: null,
    isWaitingForInput: false,
    isWaitingForConcept: false,
    concepts: null,
    recommendedConceptId: null,
    feedbackSubmitted: false,
    justGenerated: false,
    references: "",
    feedbackPresets: null,
    pipelineSteps: [],
    nodeResults: {},
    traceId: null,
    productionSnapshot: null,
    interactionMode: "auto",
    fastTrack: false,
    isWaitingForPlan: false,
    chatContext: [],
    ...overrides,
  };
}

function makeScene(overrides: Partial<SceneItem> = {}): SceneItem {
  return {
    id: 0,
    client_id: "scene-1",
    order: 0,
    script: "Hello",
    speaker: "A",
    duration: 3,
    image_prompt: "1girl",
    image_prompt_ko: "소녀",
    image_url: null,
    ...overrides,
  };
}

describe("buildSyncMeta", () => {
  it("extracts sync metadata from editor state", () => {
    const state = makeEditorState();
    const meta = buildSyncMeta(state);
    expect(meta).toEqual({
      topic: "Test Topic",
      description: "Test description",
      duration: 60,
      language: "ko",
      structure: "Monologue",
      characterId: 1,
      characterName: "Alice",
      characterBId: null,
      characterBName: null,
    });
  });

  it("trims topic and description", () => {
    const state = makeEditorState({ topic: "  padded  ", description: "  desc  " });
    const meta = buildSyncMeta(state);
    expect(meta.topic).toBe("padded");
    expect(meta.description).toBe("desc");
  });
});

describe("buildGenerateBody", () => {
  it("builds POST body with required fields", () => {
    const state = makeEditorState();
    const body = buildGenerateBody(state, 5);
    expect(body.topic).toBe("Test Topic");
    expect(body.duration).toBe(60);
    expect(body.language).toBe("ko");
    expect(body.structure).toBe("Monologue");
    expect(body.group_id).toBe(5);
    // character_id / character_b_id は Director 캐스팅 SSOT로 body에 포함하지 않음
    expect(body.character_id).toBeUndefined();
    expect(body.interaction_mode).toBe("auto");
  });

  it("omits description when empty", () => {
    const state = makeEditorState({ description: "" });
    const body = buildGenerateBody(state, 1);
    expect(body.description).toBeUndefined();
  });

  it("omits character_id when null", () => {
    const state = makeEditorState({ characterId: null });
    const body = buildGenerateBody(state, 1);
    expect(body.character_id).toBeUndefined();
  });

  it("omits character_b_id when null", () => {
    const state = makeEditorState({ characterBId: null });
    const body = buildGenerateBody(state, 1);
    expect(body.character_b_id).toBeUndefined();
  });

  it("does not include character_b_id (Director casting SSOT)", () => {
    const state = makeEditorState({ characterBId: 2 });
    const body = buildGenerateBody(state, 1);
    // Director 캐스팅 SSOT — character_b_id는 body에 포함하지 않음
    expect(body.character_b_id).toBeUndefined();
  });

  it("parses references from multi-line text", () => {
    const state = makeEditorState({ references: "ref1\nref2\n\nref3" });
    const body = buildGenerateBody(state, 1);
    expect(body.references).toEqual(["ref1", "ref2", "ref3"]);
  });

  it("omits references when empty", () => {
    const state = makeEditorState({ references: "" });
    const body = buildGenerateBody(state, 1);
    expect(body.references).toBeUndefined();
  });

  it("includes skip_stages when fastTrack is true", () => {
    const state = makeEditorState({ fastTrack: true });
    const body = buildGenerateBody(state, 1);
    expect(body.skip_stages).toEqual(["research", "concept"]);
  });

  it("omits skip_stages when fastTrack is false", () => {
    const state = makeEditorState({ fastTrack: false });
    const body = buildGenerateBody(state, 1);
    expect(body.skip_stages).toBeUndefined();
  });
});

describe("buildSavePayload", () => {
  it("builds save payload with scenes", () => {
    const scene = makeScene();
    const state = makeEditorState({ scenes: [scene] });
    const payload = buildSavePayload(state, 5);

    expect(payload.title).toBe("Test Topic");
    expect(payload.group_id).toBe(5);
    expect(payload.scenes).toHaveLength(1);
    expect(payload.scenes[0].scene_id).toBe(0);
    expect(payload.scenes[0].script).toBe("Hello");
    expect(payload.scenes[0].speaker).toBe("A");
  });

  it("includes version when present", () => {
    const state = makeEditorState({ storyboardVersion: 3 });
    const payload = buildSavePayload(state, 1);
    expect(payload.version).toBe(3);
  });

  it("omits version when null", () => {
    const state = makeEditorState({ storyboardVersion: null });
    const payload = buildSavePayload(state, 1);
    expect(payload.version).toBeUndefined();
  });

  it("maps scene fields correctly", () => {
    const scene = makeScene({
      use_controlnet: true,
      controlnet_weight: 0.8,
      voice_design_prompt: "deep voice",
      head_padding: 0.5,
      tail_padding: 0.3,
      ken_burns_preset: "zoom_in_center",
      background_id: 10,
      context_tags: { mood: "happy" },
    });
    const state = makeEditorState({ scenes: [scene] });
    const payload = buildSavePayload(state, 1);
    const s = payload.scenes[0];

    expect(s.use_controlnet).toBe(true);
    expect(s.controlnet_weight).toBe(0.8);
    expect(s.voice_design_prompt).toBe("deep voice");
    expect(s.head_padding).toBe(0.5);
    expect(s.tail_padding).toBe(0.3);
    expect(s.ken_burns_preset).toBe("zoom_in_center");
    expect(s.background_id).toBe(10);
    expect(s.context_tags).toEqual({ mood: "happy" });
  });
});

describe("handleStreamOutcome", () => {
  it("returns false when isWaiting is true", () => {
    const setState = vi.fn();
    const showToast = vi.fn();
    const dirtyRef = { current: true };

    const result = handleStreamOutcome({
      finalScenes: [makeScene()],
      isWaiting: true,
      meta: buildSyncMeta(makeEditorState()),
      setState,
      dirtyRef,
      showToast,
    });

    expect(result).toBe(false);
    expect(setState).not.toHaveBeenCalled();
  });

  it("updates state and returns true when scenes are produced", () => {
    const setState = vi.fn();
    const showToast = vi.fn();
    const dirtyRef = { current: true };
    const scenes = [makeScene()];

    const result = handleStreamOutcome({
      finalScenes: scenes,
      isWaiting: false,
      meta: buildSyncMeta(makeEditorState()),
      setState,
      dirtyRef,
      showToast,
    });

    expect(result).toBe(true);
    expect(setState).toHaveBeenCalled();
    expect(dirtyRef.current).toBe(true);
    expect(showToast).toHaveBeenCalledWith("Script generated", "success");
  });

  it("shows warning and returns false when no scenes", () => {
    const setState = vi.fn();
    const showToast = vi.fn();
    const dirtyRef = { current: false };

    const result = handleStreamOutcome({
      finalScenes: null,
      isWaiting: false,
      meta: buildSyncMeta(makeEditorState()),
      setState,
      dirtyRef,
      showToast,
    });

    expect(result).toBe(false);
    expect(showToast).toHaveBeenCalledWith("No scenes returned", "warning");
  });
});
