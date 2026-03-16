import { useCallback, useEffect } from "react";
import axios from "axios";
import { useShallow } from "zustand/react/shallow";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useRenderStore } from "../store/useRenderStore";
import { useContextStore } from "../store/useContextStore";
import { useUIStore } from "../store/useUIStore";
import { API_BASE } from "../constants";
import { getCurrentProject, hasValidProfile } from "../store/selectors/projectSelectors";
import { renderWithProgress } from "../utils/renderWithProgress";
import { getErrorMsg } from "../utils/error";

export function usePublishRender() {
  const scenes = useStoryboardStore((s) => s.scenes);
  const topic = useStoryboardStore((s) => s.topic);
  const updateScene = useStoryboardStore((s) => s.updateScene);
  const store = useRenderStore(
    useShallow((s) => ({
      layoutStyle: s.layoutStyle,
      frameStyle: s.frameStyle,
      isRendering: s.isRendering,
      includeSceneText: s.includeSceneText,
      sceneTextFont: s.sceneTextFont,
      fontList: s.fontList,
      loadedFonts: s.loadedFonts,
      kenBurnsPreset: s.kenBurnsPreset,
      kenBurnsIntensity: s.kenBurnsIntensity,
      transitionType: s.transitionType,
      speedMultiplier: s.speedMultiplier,
      audioDucking: s.audioDucking,
      bgmVolume: s.bgmVolume,
      voiceDesignPrompt: s.voiceDesignPrompt,
      voicePresetId: s.voicePresetId,
      bgmMode: s.bgmMode,
      musicPresetId: s.musicPresetId,
      bgmPrompt: s.bgmPrompt,
      bgmMood: s.bgmMood,
      renderProgress: s.renderProgress,
      videoUrl: s.videoUrl,
    }))
  );
  const setOutput = useRenderStore((s) => s.set);
  const showToast = useUIStore((s) => s.showToast);
  const projectId = useContextStore((s) => s.projectId);
  const groupId = useContextStore((s) => s.groupId);
  const storyboardId = useContextStore((s) => s.storyboardId);

  // --- Load font list on mount ---
  useEffect(() => {
    axios
      .get(`${API_BASE}/fonts/list`)
      .then((r) => setOutput({ fontList: r.data.fonts || [] }))
      .catch((err) => console.warn("[usePublishRender] Font list fetch failed:", err));
  }, [setOutput]);

  // --- Load selected font dynamically ---
  useEffect(() => {
    if (!store.sceneTextFont || store.loadedFonts.has(store.sceneTextFont)) return;
    const fontName = store.sceneTextFont;
    const fontFace = new FontFace(
      fontName,
      `url(${API_BASE}/fonts/file/${encodeURIComponent(fontName)})`
    );
    fontFace
      .load()
      .then((loaded) => {
        document.fonts.add(loaded);
        setOutput({ loadedFonts: new Set([...store.loadedFonts, fontName]) });
      })
      .catch(() => {
        setOutput({ loadedFonts: new Set([...store.loadedFonts, fontName]) });
      });
  }, [store.sceneTextFont, store.loadedFonts, setOutput]);

  // --- Disabled reason ---
  const canRender = scenes.filter((s) => !!s.image_url).length > 0;
  const getDisabledReason = (): string | null => {
    if (scenes.length === 0) return "스토리보드를 먼저 생성하세요";
    if (!hasValidProfile()) return "프로젝트를 먼저 선택하세요";
    if (!canRender) return "이미지가 있는 씬이 필요합니다";
    return null;
  };

  // --- Render ---
  const handleRender = useCallback(
    async (mode: "full" | "post") => {
      if (!hasValidProfile()) {
        showToast("프로젝트를 먼저 선택해주세요", "error");
        return;
      }
      if (!projectId || !groupId) {
        showToast("프로젝트/그룹을 먼저 선택해주세요", "error");
        return;
      }
      if (scenes.some((s) => s.image_url?.startsWith("data:"))) {
        showToast("이미지를 저장한 뒤 렌더해주세요 (data URL은 전송할 수 없습니다)", "error");
        return;
      }

      // Read latest render settings at call time (no reactive subscription needed)
      const rs = useRenderStore.getState();
      setOutput({ isRendering: true, renderProgress: null });
      try {
        const project = getCurrentProject();
        const overlaySettings =
          mode === "full" && project
            ? {
                channel_name: project.name,
                avatar_key: project.avatar_key || null,
                frame_style: rs.frameStyle,
                caption: rs.videoCaption,
                likes_count: rs.videoLikesCount,
              }
            : null;
        const postCardSettings =
          mode === "post" && project
            ? {
                channel_name: project.name,
                avatar_key: project.avatar_key || null,
                caption: rs.videoCaption,
              }
            : null;

        let renderScenes = scenes.filter((s) => s.image_url);

        // TTS prebuild: tts_asset_id 없는 씬에 대해 렌더 전 자동 생성
        if (storyboardId) {
          const missingTts = renderScenes.filter((s) => s.script?.trim() && !s.tts_asset_id);
          if (missingTts.length > 0) {
            try {
              setOutput({
                renderProgress: {
                  task_id: "prebuild",
                  stage: "setup_avatars",
                  percent: 0,
                  message: "TTS 준비 중...",
                  encode_percent: 0,
                  current_scene: 0,
                  total_scenes: missingTts.length,
                },
              });
              const prebuildRes = await axios.post(`${API_BASE}/scene/tts-prebuild`, {
                storyboard_id: storyboardId,
                scenes: missingTts.map((s) => ({
                  scene_db_id: s.id,
                  script: s.script,
                  speaker: s.speaker,
                  voice_design_prompt: s.voice_design_prompt ?? undefined,
                  scene_emotion: s.context_tags?.emotion ?? undefined,
                  image_prompt_ko: s.image_prompt_ko ?? undefined,
                })),
              });
              const results: Array<{
                scene_db_id: number;
                tts_asset_id: number | null;
                status: string;
              }> = prebuildRes.data.results ?? [];
              for (const r of results) {
                if (r.tts_asset_id && r.status === "prebuilt") {
                  const matched = renderScenes.find((s) => s.id === r.scene_db_id);
                  if (matched) updateScene(matched.client_id, { tts_asset_id: r.tts_asset_id });
                }
              }
              // Refresh renderScenes after tts_asset_id updates
              renderScenes = useStoryboardStore.getState().scenes.filter((s) => s.image_url);
            } catch (prebuildErr) {
              // prebuild 실패는 경고만 — 렌더는 계속 진행 (무음 fallback)
              console.warn("[usePublishRender] TTS prebuild failed:", prebuildErr);
            }
          }
        }

        const payload = {
          project_id: projectId,
          group_id: groupId,
          storyboard_id: storyboardId,
          scenes: renderScenes.map((s, i) => ({
            image_url: s.image_url!,
            script: s.script,
            speaker: s.speaker,
            duration: s.duration,
            order: i, // L-1: scene order
            scene_db_id: s.id || undefined, // voice_design write-back용
            image_prompt: s.image_prompt ?? undefined, // M-1
            voice_design_prompt: s.voice_design_prompt ?? undefined,
            head_padding: s.head_padding ?? undefined,
            tail_padding: s.tail_padding ?? undefined,
            background_id: s.background_id ?? undefined,
            ken_burns_preset: s.ken_burns_preset ?? undefined,
            scene_emotion: s.context_tags?.emotion ?? s.context_tags?.mood?.[0] ?? undefined,
            image_prompt_ko: s.image_prompt_ko ?? undefined,
            tts_asset_id: s.tts_asset_id ?? undefined,
          })),
          storyboard_title: topic || "my_shorts",
          layout_style: mode,
          ken_burns_preset: rs.kenBurnsPreset,
          ken_burns_intensity: rs.kenBurnsIntensity,
          transition_type: rs.transitionType,
          include_scene_text: rs.includeSceneText,
          scene_text_font: rs.sceneTextFont,
          tts_engine: rs.ttsEngine,
          voice_design_prompt: rs.voiceDesignPrompt,
          voice_preset_id: rs.voicePresetId || null,
          speed_multiplier: rs.speedMultiplier,
          bgm_file: rs.bgmFile,
          bgm_mode: rs.bgmMode,
          music_preset_id: rs.musicPresetId || null,
          bgm_prompt: rs.bgmMode === "auto" ? rs.bgmPrompt || null : null,
          audio_ducking: rs.audioDucking,
          bgm_volume: rs.bgmVolume,
          overlay_settings: overlaySettings,
          post_card_settings: postCardSettings,
        };

        const result = await renderWithProgress(payload, (p) => {
          setOutput({ renderProgress: p });
        });
        const url = result.video_url;
        if (url) {
          if (mode === "full") setOutput({ videoUrlFull: url, videoUrl: url });
          else setOutput({ videoUrlPost: url, videoUrl: url });
          const current = useRenderStore.getState().recentVideos;
          // L-4: Include project/group info in recentVideos
          const currentProject = getCurrentProject();
          const ctxState = useContextStore.getState();
          const currentGroup = ctxState.groups.find((g) => g.id === groupId);
          setOutput({
            recentVideos: [
              {
                url,
                label: mode,
                createdAt: Date.now(),
                renderHistoryId: result.render_history_id,
                projectId: projectId ?? undefined,
                projectName: currentProject?.name,
                groupId: groupId ?? undefined,
                groupName: currentGroup?.name,
              },
              ...current.slice(0, 9),
            ],
          });
        }
        showToast("Video rendered", "success");
      } catch (err) {
        showToast(`Render failed: ${getErrorMsg(err, "Unknown error")}`, "error");
      } finally {
        setOutput({ isRendering: false, renderProgress: null });
      }
    },
    [scenes, topic, setOutput, showToast, projectId, groupId, storyboardId, updateScene]
  );

  return {
    scenes,
    store,
    setOutput,
    canRender,
    disabledReason: getDisabledReason(),
    handleRender,
  };
}
