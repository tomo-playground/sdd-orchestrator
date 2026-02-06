import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { loadGroupDefaults } from "../groupActions";
import { useStudioStore } from "../../useStudioStore";

vi.mock("axios");

describe("loadGroupDefaults", () => {
  const mockSetOutput = vi.fn();
  const mockSetPlan = vi.fn();
  const mockSetEffectiveDefaults = vi.fn();
  const mockSetEffectivePreset = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(useStudioStore, "getState").mockReturnValue({
      setOutput: mockSetOutput,
      setPlan: mockSetPlan,
      setEffectiveDefaults: mockSetEffectiveDefaults,
      setEffectivePreset: mockSetEffectivePreset,
    } as never);
  });

  it("loads bgmFile from render_preset", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        render_preset: {
          name: "Test Preset",
          bgm_file: "random",
          bgm_volume: 0.25,
        },
        sources: { render_preset_id: "group" },
      },
    });

    await loadGroupDefaults(3);

    expect(mockSetOutput).toHaveBeenCalledWith(
      expect.objectContaining({
        bgmFile: "random",
        bgmVolume: 0.25,
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
          bgm_volume: 0.25,
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
      bgmVolume: 0.25,
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
});
