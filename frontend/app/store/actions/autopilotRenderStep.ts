import type { Scene } from "../../types";
import type { AutoRunStepId } from "../../types";
import { useContextStore } from "../useContextStore";
import { useRenderStore } from "../useRenderStore";
import { useStoryboardStore } from "../useStoryboardStore";
import { TTS_ENGINE } from "../../constants";
import { getCurrentProject } from "../selectors/projectSelectors";
import { renderWithProgress } from "../../utils/renderWithProgress";

type RenderStepCallbacks = {
  setAutoRunStep: (step: AutoRunStepId, msg: string) => void;
  setActiveTab: (tab: string) => void;
  pushAutoRunLog: (msg: string) => void;
};

/**
 * Execute the render step of the autopilot pipeline.
 * Builds payload from current store state, runs renderWithProgress, updates video URL.
 * Throws on missing context or render failure.
 */
export async function executeRenderStep(
  workingScenes: Scene[],
  abortSignal: AbortSignal,
  { setAutoRunStep, setActiveTab, pushAutoRunLog }: RenderStepCallbacks
): Promise<void> {
  const ctxStore = useContextStore.getState();
  const store = useRenderStore.getState();
  const { layoutStyle } = store;

  setAutoRunStep("render", `Rendering ${layoutStyle} video...`);
  setActiveTab("publish");

  const { projectId: renderProjectId, groupId: renderGroupId } = ctxStore;
  if (!renderProjectId || !renderGroupId) {
    throw new Error("Project/Group context required for render");
  }

  const project = getCurrentProject();
  const overlaySettings =
    layoutStyle === "full" && project
      ? {
          channel_name: project.name,
          avatar_key: project.avatar_key || null,
          frame_style: store.frameStyle,
          caption: store.videoCaption,
          likes_count: store.videoLikesCount,
        }
      : null;
  const postCardSettings =
    layoutStyle === "post" && project
      ? {
          channel_name: project.name,
          avatar_key: project.avatar_key || null,
          caption: store.videoCaption,
        }
      : null;

  // Guard: skip data URL images (not stored yet)
  const dataUrlScenes = workingScenes.filter((s) => s.image_url?.startsWith("data:"));
  if (dataUrlScenes.length > 0) {
    pushAutoRunLog(`Warning: ${dataUrlScenes.length} scene(s) have unstored images, skipping`);
  }
  const renderScenes = workingScenes.filter((s) => s.image_url && !s.image_url.startsWith("data:"));

  const payload = {
    project_id: renderProjectId,
    group_id: renderGroupId,
    storyboard_id: ctxStore.storyboardId,
    storyboard_title: useStoryboardStore.getState().topic || "my_shorts",
    scenes: renderScenes.map((s, i) => ({
      image_url: s.image_url,
      script: s.script,
      speaker: s.speaker,
      duration: s.duration,
      order: i,
      scene_db_id: s.id || undefined,
      image_prompt: s.image_prompt ?? undefined,
      voice_design_prompt: s.voice_design_prompt ?? undefined,
      head_padding: s.head_padding ?? undefined,
      tail_padding: s.tail_padding ?? undefined,
      background_id: s.background_id ?? undefined,
      ken_burns_preset: s.ken_burns_preset ?? undefined,
      scene_emotion: s.context_tags?.emotion ?? s.context_tags?.mood?.[0] ?? undefined,
      image_prompt_ko: s.image_prompt_ko ?? undefined,
      tts_asset_id: s.tts_asset_id ?? undefined,
    })),
    layout_style: layoutStyle,
    ken_burns_preset: store.kenBurnsPreset,
    ken_burns_intensity: store.kenBurnsIntensity,
    transition_type: store.transitionType,
    speed_multiplier: store.speedMultiplier,
    bgm_file: store.bgmFile,
    bgm_mode: store.bgmMode,
    music_preset_id: store.musicPresetId || null,
    bgm_prompt: store.bgmMode === "auto" ? store.bgmPrompt || null : null,
    audio_ducking: store.audioDucking,
    bgm_volume: store.bgmVolume,
    include_scene_text: store.includeSceneText,
    scene_text_font: store.sceneTextFont,
    tts_engine: TTS_ENGINE,
    voice_design_prompt: store.voiceDesignPrompt || null,
    voice_preset_id: store.voicePresetId || null,
    overlay_settings: overlaySettings,
    post_card_settings: postCardSettings,
  };

  const result = await renderWithProgress(
    payload,
    (p) => {
      pushAutoRunLog(`Rendering... ${p.percent}% (${p.message || p.stage})`);
    },
    abortSignal
  );

  const videoUrl = result.video_url;
  if (!videoUrl) throw new Error(`${layoutStyle} render failed`);

  const withTs = `${videoUrl}?t=${Date.now()}`;
  const currentProject = getCurrentProject();
  const currentGroup = ctxStore.groups.find((g) => g.id === renderGroupId);

  useRenderStore.getState().set({
    videoUrl: withTs,
    ...(layoutStyle === "full" ? { videoUrlFull: withTs } : { videoUrlPost: withTs }),
    recentVideos: [
      {
        url: withTs,
        label: layoutStyle,
        createdAt: Date.now(),
        renderHistoryId: result.render_history_id,
        projectId: renderProjectId,
        projectName: currentProject?.name,
        groupId: renderGroupId,
        groupName: currentGroup?.name,
      },
      ...useRenderStore.getState().recentVideos.slice(0, 9),
    ],
  });

  pushAutoRunLog(`${layoutStyle} render complete`);
}
