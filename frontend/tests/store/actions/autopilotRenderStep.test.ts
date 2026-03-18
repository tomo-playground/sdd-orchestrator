import { describe, it, expect, vi, beforeEach } from "vitest";

// localStorage mock (required by Zustand persist stores)
vi.hoisted(() => {
  const store: Record<string, string> = {};
  const mock: Storage = {
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
  globalThis.localStorage = mock;
});

import { executeRenderStep } from "../../../app/store/actions/autopilotRenderStep";
import { useContextStore } from "../../../app/store/useContextStore";
import { useRenderStore } from "../../../app/store/useRenderStore";
import { useStoryboardStore } from "../../../app/store/useStoryboardStore";
import * as renderWithProgressModule from "../../../app/utils/renderWithProgress";
import * as projectSelectors from "../../../app/store/selectors/projectSelectors";
import type { Scene } from "../../../app/types";

vi.mock("axios");
vi.mock("../../../app/utils/renderWithProgress", () => ({
  renderWithProgress: vi.fn(),
}));
vi.mock("../../../app/store/selectors/projectSelectors", () => ({
  getCurrentProject: vi.fn(() => null),
}));

// ── helpers ────────────────────────────────────────────────

function makeScene(overrides: Partial<Scene> = {}): Scene {
  return {
    id: 10,
    client_id: "scene-1",
    order: 0,
    script: "테스트 스크립트",
    speaker: "Narrator",
    duration: 3,
    image_prompt: "1girl",
    image_prompt_ko: "소녀",
    image_url: "http://localhost:9000/img.png",
    negative_prompt: "lowres",
    isGenerating: false,
    debug_payload: "",
    tts_asset_id: 5,
    ...overrides,
  } as Scene;
}

function makeCallbacks() {
  return {
    setAutoRunStep: vi.fn(),
    setActiveTab: vi.fn(),
    pushAutoRunLog: vi.fn(),
  };
}

function mockDefaultStores() {
  vi.spyOn(useContextStore, "getState").mockReturnValue({
    projectId: 1,
    groupId: 2,
    storyboardId: 42,
    groups: [],
    projects: [],
  } as never);

  vi.spyOn(useRenderStore, "getState").mockReturnValue({
    layoutStyle: "full",
    frameStyle: "default",
    kenBurnsPreset: "slow_zoom",
    kenBurnsIntensity: 1.0,
    transitionType: "fade",
    speedMultiplier: 1.0,
    bgmFile: null,
    bgmMode: "manual",
    musicPresetId: null,
    bgmPrompt: "",
    isAudioDuckingEnabled: true,
    bgmVolume: 0.3,
    isSceneTextIncluded: true,
    sceneTextFont: "NotoSansKR",
    voiceDesignPrompt: null,
    voicePresetId: null,
    videoCaption: "",
    videoLikesCount: "0",
    recentVideos: [],
    set: vi.fn(),
  } as never);

  vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
    topic: "test topic",
  } as never);
}

// ── tests ──────────────────────────────────────────────────

describe("executeRenderStep", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDefaultStores();
    (projectSelectors.getCurrentProject as ReturnType<typeof vi.fn>).mockReturnValue({
      name: "My Channel",
      avatar_key: null,
    });
  });

  describe("abort signal 처리", () => {
    it("abort된 signal이 전달되면 renderWithProgress 호출 전 AbortError throw", async () => {
      const abortController = new AbortController();
      abortController.abort();

      const renderWithProgressMock = renderWithProgressModule.renderWithProgress as ReturnType<
        typeof vi.fn
      >;
      // renderWithProgress가 AbortError를 throw하도록 설정 (axios가 abort signal 처리)
      renderWithProgressMock.mockRejectedValue(new DOMException("Aborted", "AbortError"));

      const callbacks = makeCallbacks();
      const scenes = [makeScene()];

      const error = await executeRenderStep(scenes, abortController.signal, callbacks).catch(
        (e) => e
      );
      expect(error).toBeInstanceOf(DOMException);
      expect(error.name).toBe("AbortError");

      // setAutoRunStep("render", ...) 은 abort 전에 호출됨
      expect(callbacks.setAutoRunStep).toHaveBeenCalledWith("render", expect.any(String));
    });
  });

  describe("정상 렌더 흐름", () => {
    it("renderWithProgress 성공 시 pushAutoRunLog에 video URL 메시지 기록", async () => {
      const videoUrl = "http://localhost:9000/videos/output.mp4";
      (renderWithProgressModule.renderWithProgress as ReturnType<typeof vi.fn>).mockResolvedValue({
        video_url: videoUrl,
        render_history_id: 99,
        stage: "completed",
        percent: 100,
        message: "완료",
        task_id: "task-1",
        encode_percent: 100,
        current_scene: 5,
        total_scenes: 5,
      });

      const callbacks = makeCallbacks();
      const scenes = [makeScene()];
      const controller = new AbortController();

      await executeRenderStep(scenes, controller.signal, callbacks);

      // 완료 로그에 layoutStyle("full") 포함 확인
      expect(callbacks.pushAutoRunLog).toHaveBeenCalledWith(expect.stringContaining("full"));
      expect(callbacks.pushAutoRunLog).toHaveBeenCalledWith(expect.stringContaining("complete"));
    });

    it("renderWithProgress 성공 시 useRenderStore.set 호출 (videoUrl 업데이트)", async () => {
      const videoUrl = "http://localhost:9000/videos/output.mp4";
      (renderWithProgressModule.renderWithProgress as ReturnType<typeof vi.fn>).mockResolvedValue({
        video_url: videoUrl,
        render_history_id: 77,
        stage: "completed",
        percent: 100,
        message: "",
        task_id: "task-2",
        encode_percent: 100,
        current_scene: 1,
        total_scenes: 1,
      });

      const setMock = vi.fn();
      vi.spyOn(useRenderStore, "getState").mockReturnValue({
        ...useRenderStore.getState(),
        set: setMock,
        recentVideos: [],
        layoutStyle: "full",
        frameStyle: "default",
        kenBurnsPreset: "slow_zoom",
        kenBurnsIntensity: 1.0,
        transitionType: "fade",
        speedMultiplier: 1.0,
        bgmFile: null,
        bgmMode: "manual",
        musicPresetId: null,
        bgmPrompt: "",
        isAudioDuckingEnabled: true,
        bgmVolume: 0.3,
        isSceneTextIncluded: true,
        sceneTextFont: "NotoSansKR",
        voiceDesignPrompt: null,
        voicePresetId: null,
        videoCaption: "",
        videoLikesCount: "0",
      } as never);

      const controller = new AbortController();
      await executeRenderStep([makeScene()], controller.signal, makeCallbacks());

      expect(setMock).toHaveBeenCalledWith(
        expect.objectContaining({
          videoUrl: expect.stringContaining(videoUrl),
        })
      );
    });

    it("video_url이 없으면 에러 throw", async () => {
      (renderWithProgressModule.renderWithProgress as ReturnType<typeof vi.fn>).mockResolvedValue({
        video_url: null,
        stage: "completed",
        percent: 100,
        message: "",
        task_id: "task-3",
        encode_percent: 100,
        current_scene: 1,
        total_scenes: 1,
      });

      const controller = new AbortController();
      await expect(
        executeRenderStep([makeScene()], controller.signal, makeCallbacks())
      ).rejects.toThrow("render failed");
    });
  });

  describe("페이로드 구조 검증 (Smoke Test)", () => {
    it("씬의 scene_db_id와 tts_asset_id가 payload에 포함됨", async () => {
      let capturedPayload: Record<string, unknown> | null = null;
      (renderWithProgressModule.renderWithProgress as ReturnType<typeof vi.fn>).mockImplementation(
        async (payload) => {
          capturedPayload = payload as Record<string, unknown>;
          return {
            video_url: "http://localhost:9000/v.mp4",
            render_history_id: 1,
            stage: "completed",
            percent: 100,
            message: "",
            task_id: "t",
            encode_percent: 100,
            current_scene: 1,
            total_scenes: 1,
          };
        }
      );

      const scene = makeScene({
        id: 99,
        tts_asset_id: 55,
        image_url: "http://localhost:9000/img.png",
        script: "테스트",
        speaker: "A",
      });

      const setMock = vi.fn();
      vi.spyOn(useRenderStore, "getState").mockReturnValue({
        layoutStyle: "full",
        frameStyle: "default",
        kenBurnsPreset: "slow_zoom",
        kenBurnsIntensity: 1.0,
        transitionType: "fade",
        speedMultiplier: 1.0,
        bgmFile: null,
        bgmMode: "manual",
        musicPresetId: null,
        bgmPrompt: "",
        isAudioDuckingEnabled: true,
        bgmVolume: 0.3,
        isSceneTextIncluded: true,
        sceneTextFont: "NotoSansKR",
        voiceDesignPrompt: null,
        voicePresetId: null,
        videoCaption: "",
        videoLikesCount: "0",
        recentVideos: [],
        set: setMock,
      } as never);

      const controller = new AbortController();
      await executeRenderStep([scene], controller.signal, makeCallbacks());

      expect(capturedPayload).not.toBeNull();
      const scenes = capturedPayload!.scenes as Array<Record<string, unknown>>;
      expect(scenes).toHaveLength(1);

      const scenePayload = scenes[0];
      expect(scenePayload.scene_db_id).toBe(99);
      expect(scenePayload.tts_asset_id).toBe(55);
    });

    it("data: URL 이미지를 가진 씬은 렌더 페이로드에서 제외됨", async () => {
      let capturedPayload: Record<string, unknown> | null = null;
      (renderWithProgressModule.renderWithProgress as ReturnType<typeof vi.fn>).mockImplementation(
        async (payload) => {
          capturedPayload = payload as Record<string, unknown>;
          return {
            video_url: "http://localhost:9000/v.mp4",
            render_history_id: 1,
            stage: "completed",
            percent: 100,
            message: "",
            task_id: "t",
            encode_percent: 100,
            current_scene: 1,
            total_scenes: 1,
          };
        }
      );

      const setMock = vi.fn();
      vi.spyOn(useRenderStore, "getState").mockReturnValue({
        layoutStyle: "full",
        frameStyle: "default",
        kenBurnsPreset: "slow_zoom",
        kenBurnsIntensity: 1.0,
        transitionType: "fade",
        speedMultiplier: 1.0,
        bgmFile: null,
        bgmMode: "manual",
        musicPresetId: null,
        bgmPrompt: "",
        isAudioDuckingEnabled: true,
        bgmVolume: 0.3,
        isSceneTextIncluded: true,
        sceneTextFont: "NotoSansKR",
        voiceDesignPrompt: null,
        voicePresetId: null,
        videoCaption: "",
        videoLikesCount: "0",
        recentVideos: [],
        set: setMock,
      } as never);

      const storedScene = makeScene({ id: 1, image_url: "http://localhost:9000/real.png" });
      const dataUrlScene = makeScene({ id: 2, image_url: "data:image/png;base64,abc123" });

      const controller = new AbortController();
      const callbacks = makeCallbacks();
      await executeRenderStep([storedScene, dataUrlScene], controller.signal, callbacks);

      expect(capturedPayload).not.toBeNull();
      const scenes = capturedPayload!.scenes as Array<Record<string, unknown>>;
      // data: URL 씬은 제외되어야 함
      expect(scenes).toHaveLength(1);
      expect(scenes[0].scene_db_id).toBe(1);

      // Warning 로그 확인
      expect(callbacks.pushAutoRunLog).toHaveBeenCalledWith(expect.stringContaining("unstored"));
    });

    it("project_id, group_id, storyboard_id가 payload에 포함됨", async () => {
      let capturedPayload: Record<string, unknown> | null = null;
      (renderWithProgressModule.renderWithProgress as ReturnType<typeof vi.fn>).mockImplementation(
        async (payload) => {
          capturedPayload = payload as Record<string, unknown>;
          return {
            video_url: "http://localhost:9000/v.mp4",
            render_history_id: 1,
            stage: "completed",
            percent: 100,
            message: "",
            task_id: "t",
            encode_percent: 100,
            current_scene: 1,
            total_scenes: 1,
          };
        }
      );

      const setMock = vi.fn();
      vi.spyOn(useRenderStore, "getState").mockReturnValue({
        layoutStyle: "full",
        frameStyle: "default",
        kenBurnsPreset: "slow_zoom",
        kenBurnsIntensity: 1.0,
        transitionType: "fade",
        speedMultiplier: 1.0,
        bgmFile: null,
        bgmMode: "manual",
        musicPresetId: null,
        bgmPrompt: "",
        isAudioDuckingEnabled: true,
        bgmVolume: 0.3,
        isSceneTextIncluded: true,
        sceneTextFont: "NotoSansKR",
        voiceDesignPrompt: null,
        voicePresetId: null,
        videoCaption: "",
        videoLikesCount: "0",
        recentVideos: [],
        set: setMock,
      } as never);

      const controller = new AbortController();
      await executeRenderStep([makeScene()], controller.signal, makeCallbacks());

      expect(capturedPayload).not.toBeNull();
      expect(capturedPayload!.project_id).toBe(1);
      expect(capturedPayload!.group_id).toBe(2);
      expect(capturedPayload!.storyboard_id).toBe(42);
    });
  });

  describe("컨텍스트 누락 처리", () => {
    it("projectId가 null이면 에러 throw (렌더 전 조기 실패)", async () => {
      vi.spyOn(useContextStore, "getState").mockReturnValue({
        projectId: null,
        groupId: 2,
        storyboardId: 42,
        groups: [],
        projects: [],
      } as never);

      const controller = new AbortController();
      await expect(
        executeRenderStep([makeScene()], controller.signal, makeCallbacks())
      ).rejects.toThrow("Project/Group context required for render");
    });

    it("groupId가 null이면 에러 throw", async () => {
      vi.spyOn(useContextStore, "getState").mockReturnValue({
        projectId: 1,
        groupId: null,
        storyboardId: 42,
        groups: [],
        projects: [],
      } as never);

      const controller = new AbortController();
      await expect(
        executeRenderStep([makeScene()], controller.signal, makeCallbacks())
      ).rejects.toThrow("Project/Group context required for render");
    });
  });
});
