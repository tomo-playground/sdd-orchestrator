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
import { useStoryboardStore } from "../../app/store/useStoryboardStore";
import type { Scene } from "../../app/types";

function makeScene(overrides: Partial<Scene> = {}): Scene {
  return {
    id: 1,
    client_id: "scene-1",
    order: 0,
    script: "테스트 대사",
    speaker: "A" as const,
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

describe("SceneEssentialFields — DoD-5: Speaker dropdown character names", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    useStoryboardStore.getState().reset();
  });

  it("shows 'A: 재민' when selectedCharacterName is set", () => {
    useStoryboardStore.setState({ selectedCharacterName: "재민" });

    render(
      <SceneEssentialFields
        scene={makeScene()}
        structure="solo"
        onUpdateScene={vi.fn()}
        onSpeakerChange={vi.fn()}
        onImageUpload={vi.fn()}
      />
    );

    const option = screen.getByRole("option", { name: /A: 재민/ });
    expect(option).toBeInTheDocument();
  });

  it("shows 'Actor A' fallback when no character name", () => {
    useStoryboardStore.setState({ selectedCharacterName: null });

    render(
      <SceneEssentialFields
        scene={makeScene()}
        structure="solo"
        onUpdateScene={vi.fn()}
        onSpeakerChange={vi.fn()}
        onImageUpload={vi.fn()}
      />
    );

    const option = screen.getByRole("option", { name: "Actor A" });
    expect(option).toBeInTheDocument();
  });

  it("shows 'B: 하은' for character B in multi-char structure", () => {
    useStoryboardStore.setState({
      selectedCharacterName: "재민",
      selectedCharacterBName: "하은",
    });

    render(
      <SceneEssentialFields
        scene={makeScene()}
        structure="dialogue"
        onUpdateScene={vi.fn()}
        onSpeakerChange={vi.fn()}
        onImageUpload={vi.fn()}
      />
    );

    expect(screen.getByRole("option", { name: /A: 재민/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /B: 하은/ })).toBeInTheDocument();
  });

  it("shows 'Actor B' fallback for character B when no name", () => {
    useStoryboardStore.setState({
      selectedCharacterName: "재민",
      selectedCharacterBName: null,
    });

    render(
      <SceneEssentialFields
        scene={makeScene()}
        structure="dialogue"
        onUpdateScene={vi.fn()}
        onSpeakerChange={vi.fn()}
        onImageUpload={vi.fn()}
      />
    );

    expect(screen.getByRole("option", { name: /A: 재민/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Actor B" })).toBeInTheDocument();
  });
});
