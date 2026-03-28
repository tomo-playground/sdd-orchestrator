import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

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

import SceneEssentialFields from "../../app/components/storyboard/SceneEssentialFields";
import { SceneProvider } from "../../app/components/storyboard/SceneContext";
import type { SceneContextValue } from "../../app/components/storyboard/SceneContext";
import { useStoryboardStore } from "../../app/store/useStoryboardStore";
import type { Scene } from "../../app/types";

function makeScene(overrides: Partial<Scene> = {}): Scene {
  return {
    id: 1,
    client_id: "scene-1",
    order: 0,
    script: "테스트 대사",
    speaker: "speaker_1" as const,
    duration: 3,
    image_prompt: "",
    image_prompt_ko: "",
    image_url: null,
    negative_prompt: "",
    isGenerating: false,
    debug_payload: "",
    context_tags: {},
    voice_design_prompt: null,
    tts_asset_id: null,
    ...overrides,
  } as Scene;
}

function makeContextValue(scene: Scene, structure: string): SceneContextValue {
  return {
    data: {
      scene,
      loraTriggerWords: [],
      characterLoras: [],
      tagsByGroup: {},
      sceneTagGroups: [],
      isExclusiveGroup: () => false,
      basePromptA: "",
      sceneMenuOpen: false,
      sceneIndex: 0,
      isMarkingStatus: false,
      structure,
    },
    callbacks: {
      onUpdateScene: vi.fn(),
      onRemoveScene: vi.fn(),
      onSpeakerChange: vi.fn(),
      onImageUpload: vi.fn(),
      onGenerateImage: vi.fn(),
      onApplyMissingTags: vi.fn(),
      onImagePreview: vi.fn(),
      buildNegativePrompt: vi.fn(() => ""),
      buildScenePrompt: vi.fn(() => null),
      showToast: vi.fn(),
      onSceneMenuToggle: vi.fn(),
      onSceneMenuClose: vi.fn(),
    },
  };
}

function renderWithContext(scene: Scene, structure: string) {
  const ctxValue = makeContextValue(scene, structure);
  return render(
    <SceneProvider value={ctxValue}>
      <SceneEssentialFields scene={scene} />
    </SceneProvider>
  );
}

describe("SceneEssentialFields — DoD-5: Speaker dropdown character names", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    useStoryboardStore.getState().reset();
  });

  it("shows '1: 재민' when selectedCharacterName is set", () => {
    useStoryboardStore.setState({ selectedCharacterName: "재민" });
    renderWithContext(makeScene(), "solo");

    const option = screen.getByRole("option", { name: /1: 재민/ });
    expect(option).toBeInTheDocument();
  });

  it("shows 'Speaker 1' fallback when no character name", () => {
    useStoryboardStore.setState({ selectedCharacterName: null });
    renderWithContext(makeScene(), "solo");

    const option = screen.getByRole("option", { name: "Speaker 1" });
    expect(option).toBeInTheDocument();
  });

  it("shows '2: 하은' for character B in multi-char structure", () => {
    useStoryboardStore.setState({
      selectedCharacterName: "재민",
      selectedCharacterBName: "하은",
    });
    renderWithContext(makeScene(), "dialogue");

    expect(screen.getByRole("option", { name: /1: 재민/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /2: 하은/ })).toBeInTheDocument();
  });

  it("shows 'Speaker 2' fallback for character B when no name", () => {
    useStoryboardStore.setState({
      selectedCharacterName: "재민",
      selectedCharacterBName: null,
    });
    renderWithContext(makeScene(), "dialogue");

    expect(screen.getByRole("option", { name: /1: 재민/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Speaker 2" })).toBeInTheDocument();
  });
});
