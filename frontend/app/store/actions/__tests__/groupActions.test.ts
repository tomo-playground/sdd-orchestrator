import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { loadGroupDefaults } from "../groupActions";
import { useContextStore } from "../../useContextStore";
import { useRenderStore } from "../../useRenderStore";
import { useStoryboardStore } from "../../useStoryboardStore";

vi.mock("axios");
vi.mock("../styleProfileActions", () => ({
  loadStyleProfileFromId: vi.fn().mockResolvedValue(undefined),
}));

describe("loadGroupDefaults", () => {
  const mockSetOutput = vi.fn();
  const mockSetPlan = vi.fn();
  const mockSetEffectiveDefaults = vi.fn();
  const mockSetEffectivePreset = vi.fn();
  const mockSetEffectiveSdParams = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(useContextStore, "getState").mockReturnValue({
      setEffectiveDefaults: mockSetEffectiveDefaults,
      setEffectivePreset: mockSetEffectivePreset,
      setEffectiveSdParams: mockSetEffectiveSdParams,
    } as never);
    vi.spyOn(useRenderStore, "getState").mockReturnValue({
      set: mockSetOutput,
      currentStyleProfile: null,
    } as never);
    vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
      set: mockSetPlan,
    } as never);
  });

  it("loads bgmFile from render_preset", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        render_preset: {
          name: "Test Preset",
          bgm_file: "random",
          bgm_volume: 0.4,
        },
        sources: { render_preset_id: "group" },
      },
    });

    await loadGroupDefaults(3);

    expect(mockSetOutput).toHaveBeenCalledWith(
      expect.objectContaining({
        bgmFile: "random",
        bgmVolume: 0.4,
      })
    );
  });

  it("loads speedMultiplier from render_preset", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        render_preset: {
          name: "Test Preset",
          speed_multiplier: 1.3,
        },
        sources: { render_preset_id: "group" },
      },
    });

    await loadGroupDefaults(3);

    expect(mockSetOutput).toHaveBeenCalledWith(
      expect.objectContaining({
        speedMultiplier: 1.3,
      })
    );
  });

  it("loads voicePresetId from narrator_voice_preset_id", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        render_preset: { name: "Test Preset" },
        narrator_voice_preset_id: 12,
        sources: { render_preset_id: "group" },
      },
    });

    await loadGroupDefaults(3);

    expect(mockSetOutput).toHaveBeenCalledWith(
      expect.objectContaining({
        voicePresetId: 12,
      })
    );
  });

  it("loads all render preset fields", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        render_preset: {
          name: "Post 표준",
          bgm_file: "random",
          bgm_volume: 0.4,
          audio_ducking: true,
          scene_text_font: "온글잎 박다현체.ttf",
          layout_style: "post",
          frame_style: "overlay_minimal.png",
          transition_type: "random",
          ken_burns_preset: "random",
          ken_burns_intensity: 1.0,
          speed_multiplier: 1.3,
        },
        narrator_voice_preset_id: 12,
        sources: { render_preset_id: "group" },
      },
    });

    await loadGroupDefaults(3);

    expect(mockSetOutput).toHaveBeenCalledWith({
      bgmFile: "random",
      bgmVolume: 0.4,
      audioDucking: true,
      sceneTextFont: "온글잎 박다현체.ttf",
      layoutStyle: "post",
      frameStyle: "overlay_minimal.png",
      transitionType: "random",
      kenBurnsPreset: "random",
      kenBurnsIntensity: 1.0,
      speedMultiplier: 1.3,
      voicePresetId: 12,
    });
  });

  it("loads language/structure/duration to plan slice", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        render_preset: { name: "Test" },
        language: "Korean",
        structure: "Monologue",
        duration: 30,
        sources: {},
      },
    });

    await loadGroupDefaults(3);

    expect(mockSetPlan).toHaveBeenCalledWith({
      language: "Korean",
      structure: "Monologue",
      duration: 30,
    });
  });

  it("sets effective preset name and source", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        render_preset: { name: "Post 표준" },
        sources: { render_preset_id: "group" },
      },
    });

    await loadGroupDefaults(3);

    expect(mockSetEffectivePreset).toHaveBeenCalledWith("Post 표준", "group");
  });

  it("handles missing render_preset gracefully", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        render_preset: null,
        sources: {},
      },
    });

    await loadGroupDefaults(3);

    expect(mockSetEffectivePreset).toHaveBeenCalledWith(null, null);
    expect(mockSetOutput).not.toHaveBeenCalled();
  });

  it("handles API error gracefully", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Network error")
    );

    await loadGroupDefaults(3);

    expect(mockSetEffectiveDefaults).toHaveBeenCalledWith(null, null, true);
  });

  describe("skipContentDefaults option", () => {
    it("skips content defaults when skipContentDefaults is true", async () => {
      (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
        data: {
          render_preset: { name: "Test", bgm_file: "random" },
          language: "Korean",
          structure: "Monologue",
          duration: 30,
          sources: { render_preset_id: "group" },
        },
      });

      await loadGroupDefaults(3, { skipContentDefaults: true });

      // Render preset should still be applied
      expect(mockSetOutput).toHaveBeenCalledWith(expect.objectContaining({ bgmFile: "random" }));
      // Content defaults (language/structure/duration) should NOT be applied
      expect(mockSetPlan).not.toHaveBeenCalled();
    });

    it("applies content defaults when skipContentDefaults is false", async () => {
      (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
        data: {
          render_preset: { name: "Test" },
          language: "Korean",
          structure: "Dialogue",
          duration: 45,
          sources: {},
        },
      });

      await loadGroupDefaults(3, { skipContentDefaults: false });

      expect(mockSetPlan).toHaveBeenCalledWith({
        language: "Korean",
        structure: "Dialogue",
        duration: 45,
      });
    });

    it("applies content defaults when options is undefined (default behavior)", async () => {
      (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
        data: {
          render_preset: { name: "Test" },
          language: "English",
          structure: "Narrated Dialogue",
          duration: 60,
          sources: {},
        },
      });

      await loadGroupDefaults(3);

      expect(mockSetPlan).toHaveBeenCalledWith({
        language: "English",
        structure: "Narrated Dialogue",
        duration: 60,
      });
    });

    it("preserves storyboard structure when loading existing storyboard", async () => {
      // Scenario: User loads storyboard with structure="Dialogue" from a group with default structure="Monologue"
      // The storyboard's structure should be preserved, not overwritten by group default
      (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
        data: {
          render_preset: { name: "Test", speed_multiplier: 1.2 },
          language: "Korean",
          structure: "Monologue", // Group default
          duration: 30,
          sources: {},
        },
      });

      // When skipContentDefaults is true (existing storyboard scenario)
      await loadGroupDefaults(3, { skipContentDefaults: true });

      // Render settings should be applied
      expect(mockSetOutput).toHaveBeenCalledWith(expect.objectContaining({ speedMultiplier: 1.2 }));
      // But structure/language/duration should NOT overwrite storyboard values
      expect(mockSetPlan).not.toHaveBeenCalled();
    });
  });
});
