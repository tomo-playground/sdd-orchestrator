import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { SceneProvider, useSceneContext } from "../SceneContext";
import type { SceneDataContext, SceneCallbacksContext } from "../SceneContext";

function makeContextValue(overrides?: {
  data?: Partial<SceneDataContext>;
  callbacks?: Partial<SceneCallbacksContext>;
}) {
  return {
    data: {
      loraTriggerWords: [],
      characterLoras: [],
      tagsByGroup: {},
      sceneTagGroups: [],
      isExclusiveGroup: () => false,
      basePromptA: "",
      sceneMenuOpen: false,
      sceneIndex: 0,
      isMarkingStatus: false,
      ...overrides?.data,
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
      ...overrides?.callbacks,
    },
  };
}

describe("SceneContext", () => {
  it("throws when useSceneContext is called outside SceneProvider", () => {
    // Suppress console.error for expected error
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useSceneContext())).toThrow(
      "useSceneContext must be used within a SceneProvider"
    );
    spy.mockRestore();
  });

  it("provides data and callbacks within SceneProvider", () => {
    const value = makeContextValue();
    const { result } = renderHook(() => useSceneContext(), {
      wrapper: ({ children }) => <SceneProvider value={value}>{children}</SceneProvider>,
    });
    expect(result.current.data).toBe(value.data);
    expect(result.current.callbacks).toBe(value.callbacks);
  });

  it("provides TTS fields in data context", () => {
    const ttsState = {
      status: "playing" as const,
      audioUrl: "http://example.com/audio.wav",
      duration: 3.5,
      cacheKey: "key-1",
      error: null,
      voiceDesign: "neutral",
      voiceSeed: 42,
    };
    const value = makeContextValue({ data: { ttsState } });
    const { result } = renderHook(() => useSceneContext(), {
      wrapper: ({ children }) => <SceneProvider value={value}>{children}</SceneProvider>,
    });
    expect(result.current.data.ttsState).toEqual(ttsState);
  });

  it("provides TTS callbacks in callbacks context", () => {
    const onTTSPreview = vi.fn();
    const onTTSRegenerate = vi.fn();
    const audioPlayer = { playingUrl: null, play: vi.fn(), stop: vi.fn() };
    const value = makeContextValue({
      callbacks: { onTTSPreview, onTTSRegenerate, audioPlayer },
    });
    const { result } = renderHook(() => useSceneContext(), {
      wrapper: ({ children }) => <SceneProvider value={value}>{children}</SceneProvider>,
    });
    expect(result.current.callbacks.onTTSPreview).toBe(onTTSPreview);
    expect(result.current.callbacks.onTTSRegenerate).toBe(onTTSRegenerate);
    expect(result.current.callbacks.audioPlayer).toBe(audioPlayer);
  });

  it("renders correctly when ttsState is undefined (optional)", () => {
    const value = makeContextValue();
    const { result } = renderHook(() => useSceneContext(), {
      wrapper: ({ children }) => <SceneProvider value={value}>{children}</SceneProvider>,
    });
    expect(result.current.data.ttsState).toBeUndefined();
  });
});
