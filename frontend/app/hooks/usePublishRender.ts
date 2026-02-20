import { useCallback, useEffect, useRef, useState } from "react";
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
      bgmFile: s.bgmFile,
      bgmList: s.bgmList,
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

  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);
  const [isPreviewingBgm, setIsPreviewingBgm] = useState(false);

  // --- Load lists on mount ---
  useEffect(() => {
    axios
      .get(`${API_BASE}/audio/list`)
      .then((r) => setOutput({ bgmList: r.data.audios || [] }))
      .catch(() => {});
    axios
      .get(`${API_BASE}/fonts/list`)
      .then((r) => setOutput({ fontList: r.data.fonts || [] }))
      .catch(() => {});
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

  // --- Cleanup audio on unmount ---
  useEffect(() => () => stopBgmPreview(), []);

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
                avatar_key: project.avatar_key || project.handle || project.name,
                frame_style: rs.frameStyle,
                caption: rs.videoCaption,
                likes_count: rs.videoLikesCount,
              }
            : null;
        const postCardSettings =
          mode === "post" && project
            ? {
                channel_name: project.name,
                avatar_key: project.avatar_key || project.handle || project.name,
                caption: rs.videoCaption,
              }
            : null;

        const payload = {
          project_id: projectId,
          group_id: groupId,
          storyboard_id: storyboardId,
          scenes: scenes
            .filter((s) => s.image_url)
            .map((s) => ({
              image_url: s.image_url!,
              script: s.script,
              speaker: s.speaker,
              duration: s.duration,
            })),
          storyboard_title: topic || "my_shorts",
          layout_style: mode,
          ken_burns_preset: rs.kenBurnsPreset,
          ken_burns_intensity: rs.kenBurnsIntensity,
          transition_type: rs.transitionType,
          include_scene_text: rs.includeSceneText,
          scene_text_font: rs.sceneTextFont,
          tts_engine: "qwen",
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
          setOutput({
            recentVideos: [
              {
                url,
                label: mode,
                createdAt: Date.now(),
                renderHistoryId: result.render_history_id,
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
    [scenes, topic, setOutput, showToast, projectId, groupId, storyboardId]
  );

  // --- BGM Preview ---
  function stopBgmPreview() {
    if (previewTimeoutRef.current) {
      window.clearTimeout(previewTimeoutRef.current);
      previewTimeoutRef.current = null;
    }
    if (previewAudioRef.current) {
      previewAudioRef.current.pause();
      previewAudioRef.current.currentTime = 0;
    }
    setIsPreviewingBgm(false);
  }

  function handlePreviewBgm() {
    const { bgmList, bgmFile } = useRenderStore.getState();
    const sourceUrl = bgmList.find((b) => b.name === bgmFile)?.url ?? "";
    if (!sourceUrl) return;
    stopBgmPreview();
    const audio = new Audio(sourceUrl);
    audio.onerror = () => stopBgmPreview();
    previewAudioRef.current = audio;
    setIsPreviewingBgm(true);
    audio.play().catch(() => stopBgmPreview());
    previewTimeoutRef.current = window.setTimeout(() => stopBgmPreview(), 10000);
  }

  // --- Voice preset sync ---
  const handleSetVoicePresetId = useCallback(
    async (v: number | null) => {
      setOutput({ voicePresetId: v });
      if (groupId) {
        try {
          await axios.put(`${API_BASE}/groups/${groupId}/config`, {
            narrator_voice_preset_id: v,
          });
        } catch (err) {
          console.error("[setVoicePresetId] Failed to update group config:", err);
        }
      }
    },
    [setOutput, groupId]
  );

  return {
    scenes,
    store,
    setOutput,
    canRender,
    disabledReason: getDisabledReason(),
    handleRender,
    isPreviewingBgm,
    handlePreviewBgm,
    handleSetVoicePresetId,
  };
}
