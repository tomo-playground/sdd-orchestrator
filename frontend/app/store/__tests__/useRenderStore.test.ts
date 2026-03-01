import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";

vi.mock("axios");

// Zustand v5 persist requires localStorage mock before import
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

import { useRenderStore } from "../useRenderStore";

describe("useRenderStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    useRenderStore.getState().reset();
    useRenderStore.setState({ voicePresetsLoaded: false, voicePresets: [] });
  });

  describe("set", () => {
    it("merges partial updates", () => {
      useRenderStore.getState().set({ bgmVolume: 0.5, layoutStyle: "full" });
      expect(useRenderStore.getState().bgmVolume).toBe(0.5);
      expect(useRenderStore.getState().layoutStyle).toBe("full");
    });
  });

  describe("reset", () => {
    it("resets all fields to initial state", () => {
      useRenderStore.getState().set({ bgmVolume: 0.8, layoutStyle: "full" });
      useRenderStore.getState().reset();
      expect(useRenderStore.getState().bgmVolume).toBe(0.25);
      expect(useRenderStore.getState().layoutStyle).toBe("post");
    });
  });

  describe("fetchVoicePresets", () => {
    it("fetches and stores voice presets", async () => {
      const presets = [{ id: 1, name: "Voice 1" }];
      (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
        data: presets,
      });

      await useRenderStore.getState().fetchVoicePresets();

      expect(useRenderStore.getState().voicePresets).toEqual(presets);
      expect(useRenderStore.getState().voicePresetsLoaded).toBe(true);
    });

    it("skips fetch when already loaded", async () => {
      useRenderStore.setState({ voicePresetsLoaded: true });

      await useRenderStore.getState().fetchVoicePresets();

      expect(axios.get).not.toHaveBeenCalled();
    });

    it("handles fetch failure gracefully", async () => {
      (axios.get as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error("Network error")
      );

      await useRenderStore.getState().fetchVoicePresets();

      expect(useRenderStore.getState().voicePresets).toEqual([]);
      expect(useRenderStore.getState().voicePresetsLoaded).toBe(false);
    });
  });

  describe("initial state", () => {
    it("has correct defaults", () => {
      useRenderStore.getState().reset();
      const state = useRenderStore.getState();
      expect(state.layoutStyle).toBe("post");
      expect(state.includeSceneText).toBe(true);
      expect(state.audioDucking).toBe(true);
      expect(state.bgmVolume).toBe(0.25);
      expect(state.speedMultiplier).toBe(1.0);
      expect(state.ttsEngine).toBe("qwen");
      expect(state.isRendering).toBe(false);
      expect(state.bgmMode).toBe("manual");
    });
  });
});
