import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

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

import DirectorControlPanel from "../../app/components/studio/DirectorControlPanel";
import { useStoryboardStore } from "../../app/store/useStoryboardStore";
import { useRenderStore } from "../../app/store/useRenderStore";

function makeScene(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    client_id: `scene-${Math.random()}`,
    order: 0,
    script: "테스트 대사",
    speaker: "narrator" as const,
    duration: 3,
    image_prompt: "",
    image_prompt_ko: "",
    image_url: null,
    negative_prompt: "",
    isGenerating: false,
    debug_payload: "",
    context_tags: { emotion: "neutral" },
    voice_design_prompt: null,
    tts_asset_id: null,
    ...overrides,
  };
}

describe("DirectorControlPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    useStoryboardStore.getState().reset();
    useRenderStore.getState().reset();
  });

  it("renders emotion preset buttons", () => {
    render(<DirectorControlPanel />);
    expect(screen.getByRole("button", { name: /밝게/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /차분/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /긴장/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /감성/ })).toBeInTheDocument();
  });

  it("renders BGM preset buttons", () => {
    render(<DirectorControlPanel />);
    expect(screen.getByRole("button", { name: /경쾌/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /잔잔/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /긴박/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /로맨틱/ })).toBeInTheDocument();
  });

  it("clicking emotion preset calls setGlobalEmotion on all scenes", () => {
    const scenes = [makeScene(), makeScene()];
    useStoryboardStore.getState().setScenes(scenes);

    render(<DirectorControlPanel />);
    fireEvent.click(screen.getByRole("button", { name: /밝게/ }));

    const updated = useStoryboardStore.getState().scenes;
    expect(updated.every((s) => s.context_tags?.emotion === "excited")).toBe(true);
  });

  it("clicking BGM preset updates bgmMood, bgmPrompt, and bgmMode", () => {
    render(<DirectorControlPanel />);
    fireEvent.click(screen.getByRole("button", { name: /경쾌/ }));

    const state = useRenderStore.getState();
    expect(state.bgmMood).toBe("upbeat");
    expect(state.bgmPrompt).toBeTruthy();
    expect(state.bgmMode).toBe("auto");
  });

  it("highlights selected emotion preset", () => {
    useStoryboardStore.setState({ selectedEmotionPreset: "excited" });
    const { container } = render(<DirectorControlPanel />);

    const selected = container.querySelector("[data-preset-id='emotion-excited']");
    expect(selected).not.toBeNull();
    expect(selected?.className).toMatch(/bg-zinc-900|ring/);
  });

  it("highlights selected BGM preset", () => {
    useRenderStore.getState().set({ selectedBgmPreset: "upbeat" });
    const { container } = render(<DirectorControlPanel />);

    const selected = container.querySelector("[data-preset-id='bgm-upbeat']");
    expect(selected).not.toBeNull();
    expect(selected?.className).toMatch(/bg-zinc-900|ring/);
  });

  // DoD-7: Style Profile section removed
  it("does not render style profile section", () => {
    useRenderStore.setState({
      currentStyleProfile: {
        id: 1,
        name: "anime",
        display_name: "플랫 애니메",
        sd_model_name: null,
        loras: [],
        negative_embeddings: [],
        positive_embeddings: [],
        default_positive: null,
        default_negative: null,
        default_steps: null,
        default_cfg_scale: null,
        default_sampler_name: null,
        default_clip_skip: null,
      },
    });
    render(<DirectorControlPanel />);
    expect(screen.queryByText(/화풍/)).not.toBeInTheDocument();
    expect(screen.queryByText(/플랫 애니메/)).not.toBeInTheDocument();
  });

  // DoD-3: Apply-all button label
  it("shows TTS 전체 재생성 button with scene count", () => {
    const scenes = [makeScene(), makeScene(), makeScene()];
    useStoryboardStore.getState().setScenes(scenes);

    render(<DirectorControlPanel />);
    const btn = screen.getByRole("button", { name: /TTS 전체 재생성/ });
    expect(btn).toBeInTheDocument();
    expect(btn.textContent).toMatch(/3/);
  });

  it("clicking apply-all button calls onApplyAll callback", () => {
    const scenes = [makeScene(), makeScene()];
    useStoryboardStore.getState().setScenes(scenes);

    const onApplyAll = vi.fn();
    render(<DirectorControlPanel onApplyAll={onApplyAll} />);
    fireEvent.click(screen.getByRole("button", { name: /TTS 전체 재생성/ }));

    expect(onApplyAll).toHaveBeenCalledTimes(1);
  });

  it("clicking BGM preset updates selectedBgmPreset in render store", () => {
    render(<DirectorControlPanel />);
    fireEvent.click(screen.getByRole("button", { name: /경쾌/ }));

    expect(useRenderStore.getState().selectedBgmPreset).toBe("upbeat");
  });

  it("per-scene emotion override does not affect other scenes", () => {
    const scenes = [
      makeScene({ client_id: "s1", context_tags: { emotion: "excited" } }),
      makeScene({ client_id: "s2", context_tags: { emotion: "excited" } }),
    ];
    useStoryboardStore.getState().setScenes(scenes);

    // Override scene 1 only
    useStoryboardStore.getState().updateScene("s1", {
      context_tags: { emotion: "tense" },
    });

    const updated = useStoryboardStore.getState().scenes;
    expect(updated[0].context_tags?.emotion).toBe("tense");
    expect(updated[1].context_tags?.emotion).toBe("excited");
  });

  // DoD-1: Emotion preset toast
  it("calls showToast with emotion label on click", () => {
    const showToast = vi.fn();
    render(<DirectorControlPanel showToast={showToast} />);
    fireEvent.click(screen.getByRole("button", { name: /밝게/ }));

    expect(showToast).toHaveBeenCalledWith("음성 톤: 밝게 적용", "success");
  });

  it("does not call showToast on emotion re-click (same preset)", () => {
    useStoryboardStore.setState({ selectedEmotionPreset: "excited" });
    const showToast = vi.fn();
    render(<DirectorControlPanel showToast={showToast} />);
    fireEvent.click(screen.getByRole("button", { name: /밝게/ }));

    expect(showToast).not.toHaveBeenCalled();
  });

  // DoD-2: BGM preset toast
  it("calls showToast with BGM label on click", () => {
    const showToast = vi.fn();
    render(<DirectorControlPanel showToast={showToast} />);
    fireEvent.click(screen.getByRole("button", { name: /경쾌/ }));

    expect(showToast).toHaveBeenCalledWith("BGM: 경쾌 적용", "success");
  });

  it("does not call showToast on BGM re-click (same preset)", () => {
    useRenderStore.getState().set({ selectedBgmPreset: "upbeat" });
    const showToast = vi.fn();
    render(<DirectorControlPanel showToast={showToast} />);
    fireEvent.click(screen.getByRole("button", { name: /경쾌/ }));

    expect(showToast).not.toHaveBeenCalled();
  });

  // DoD-4: isApplying loading state
  it("shows spinner and disables button when isApplying=true", () => {
    const scenes = [makeScene()];
    useStoryboardStore.getState().setScenes(scenes);

    render(<DirectorControlPanel isApplying={true} />);
    const btn = screen.getByRole("button", { name: /재생성 중/ });
    expect(btn).toBeDisabled();
    expect(btn.textContent).toContain("재생성 중...");
  });

  it("shows normal button when isApplying=false", () => {
    const scenes = [makeScene()];
    useStoryboardStore.getState().setScenes(scenes);

    render(<DirectorControlPanel isApplying={false} />);
    const btn = screen.getByRole("button", { name: /TTS 전체 재생성/ });
    expect(btn).not.toBeDisabled();
  });
});
