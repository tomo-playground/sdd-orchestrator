import { describe, it, expect, vi } from "vitest";

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
import { useStoryboardStore } from "../../../app/store/useStoryboardStore";
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

  it("includes skip_stages and character_id when fastTrack is true", () => {
    const state = makeEditorState({ fastTrack: true, characterId: 1, characterBId: 2 });
    const body = buildGenerateBody(state, 1);
    expect(body.skip_stages).toEqual(["research", "concept", "production", "explain"]);
    expect(body.character_id).toBe(1);
    expect(body.character_b_id).toBe(2);
  });

  it("reads skip_stages from store (Backend SSOT)", () => {
    // Backend가 다른 skip_stages를 반환한 경우 스토어에 반영된 값을 사용
    useStoryboardStore.getState().set({ fastTrackSkipStages: ["research", "concept"] });
    const state = makeEditorState({ fastTrack: true, characterId: 1 });
    const body = buildGenerateBody(state, 1);
    expect(body.skip_stages).toEqual(["research", "concept"]);
    // 원복
    useStoryboardStore.getState().set({
      fastTrackSkipStages: ["research", "concept", "production", "explain"],
    });
  });

  it("omits skip_stages and character_id when fastTrack is false", () => {
    const state = makeEditorState({ fastTrack: false, characterId: 1 });
    const body = buildGenerateBody(state, 1);
    expect(body.skip_stages).toBeUndefined();
    expect(body.character_id).toBeUndefined();
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
    expect(showToast).toHaveBeenCalledWith("스크립트 생성 완료", "success");
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
    expect(showToast).toHaveBeenCalledWith("생성된 씬이 없습니다", "warning");
  });

  it("shows warning toasts when warnings are present", () => {
    const setState = vi.fn();
    const showToast = vi.fn();
    const dirtyRef = { current: false };
    const scenes = [makeScene()];

    const result = handleStreamOutcome({
      finalScenes: scenes,
      isWaiting: false,
      meta: buildSyncMeta(makeEditorState()),
      setState,
      dirtyRef,
      showToast,
      warnings: [
        "TTS Designer 실패: voice design이 누락되어 기본 음성으로 생성됩니다.",
      ],
    });

    expect(result).toBe(true);
    // success toast + warning toast
    expect(showToast).toHaveBeenCalledTimes(2);
    expect(showToast).toHaveBeenNthCalledWith(1, "스크립트 생성 완료", "success");
    expect(showToast).toHaveBeenNthCalledWith(
      2,
      "TTS Designer 실패: voice design이 누락되어 기본 음성으로 생성됩니다.",
      "warning"
    );
  });

  it("does not show warning toast when warnings is empty", () => {
    const setState = vi.fn();
    const showToast = vi.fn();
    const dirtyRef = { current: false };
    const scenes = [makeScene()];

    handleStreamOutcome({
      finalScenes: scenes,
      isWaiting: false,
      meta: buildSyncMeta(makeEditorState()),
      setState,
      dirtyRef,
      showToast,
      warnings: [],
    });

    // Only success toast, no warning toast
    expect(showToast).toHaveBeenCalledTimes(1);
    expect(showToast).toHaveBeenCalledWith("스크립트 생성 완료", "success");
  });
});
