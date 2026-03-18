import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { loadGroupDefaults } from "../groupActions";
import { useContextStore } from "../../useContextStore";
import { useRenderStore } from "../../useRenderStore";

vi.mock("axios");
vi.mock("../styleProfileActions", () => ({
  loadStyleProfileFromId: vi.fn().mockResolvedValue(undefined),
}));

describe("loadGroupDefaults", () => {
  const mockSetOutput = vi.fn();
  const mockSetEffectiveDefaults = vi.fn();
  const mockSetEffectivePreset = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(useContextStore, "getState").mockReturnValue({
      setEffectiveDefaults: mockSetEffectiveDefaults,
      setEffectivePreset: mockSetEffectivePreset,
    } as never);
    vi.spyOn(useRenderStore, "getState").mockReturnValue({
      set: mockSetOutput,
      currentStyleProfile: null,
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
          name: "Post \uD45C\uC900",
          bgm_file: "random",
          bgm_volume: 0.4,
          audio_ducking: true,
          scene_text_font: "\uC628\uAE00\uC78E \uBC15\uB2E4\uD604\uCCB4.ttf",
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
      sceneTextFont: "\uC628\uAE00\uC78E \uBC15\uB2E4\uD604\uCCB4.ttf",
      layoutStyle: "post",
      frameStyle: "overlay_minimal.png",
      transitionType: "random",
      kenBurnsPreset: "random",
      kenBurnsIntensity: 1.0,
      speedMultiplier: 1.3,
      voicePresetId: 12,
    });
  });

  it("sets effective preset name and source", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        render_preset: { name: "Post \uD45C\uC900" },
        sources: { render_preset_id: "group" },
      },
    });

    await loadGroupDefaults(3);

    expect(mockSetEffectivePreset).toHaveBeenCalledWith("Post \uD45C\uC900", "group");
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
