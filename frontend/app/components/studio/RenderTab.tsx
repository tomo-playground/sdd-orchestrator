"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { API_BASE } from "../../constants";
import RenderSettingsPanel from "../video/RenderSettingsPanel";
import { getCurrentProject, hasValidProfile } from "../../store/selectors/projectSelectors";

export default function RenderTab() {
  const store = useStudioStore();
  const {
    scenes,
    layoutStyle,
    frameStyle,
    isRendering,
    includeSceneText,
    sceneTextFont,
    fontList,
    loadedFonts,
    kenBurnsPreset,
    kenBurnsIntensity,
    transitionType,
    speedMultiplier,
    bgmFile,
    bgmList,
    audioDucking,
    bgmVolume,
    voiceDesignPrompt,
    voicePresetId,
    videoUrl,
    videoUrlFull,
    videoUrlPost,
    recentVideos,
    setOutput,
    showToast,
  } = store;

  const videoCaption = useStudioStore((s) => s.videoCaption);
  const videoLikesCount = useStudioStore((s) => s.videoLikesCount);

  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);
  const [isPreviewingBgm, setIsPreviewingBgm] = useState(false);

  // Load audio, font lists on mount
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

  // Load selected font dynamically
  useEffect(() => {
    if (!sceneTextFont || loadedFonts.has(sceneTextFont)) return;

    const fontFace = new FontFace(
      sceneTextFont,
      `url(${API_BASE}/fonts/file/${encodeURIComponent(sceneTextFont)})`
    );

    fontFace
      .load()
      .then((loaded) => {
        document.fonts.add(loaded);
        setOutput({ loadedFonts: new Set([...loadedFonts, sceneTextFont]) });
      })
      .catch((err) => {
        console.warn(`Failed to load font ${sceneTextFont}:`, err);
      });
  }, [sceneTextFont, loadedFonts, setOutput]);

  // Cleanup audio on unmount
  useEffect(() => () => stopBgmPreview(), []);

  const canRender = scenes.filter((s) => !!s.image_url).length > 0;

  // ---------- Render ----------

  const handleRender = useCallback(
    async (mode: "full" | "post") => {
      if (!hasValidProfile()) {
        showToast("프로젝트를 먼저 선택해주세요", "error");
        return;
      }

      setOutput({ isRendering: true });
      try {
        const project = getCurrentProject();
        const finalOverlaySettings = mode === "full" && project ? {
          channel_name: project.name,
          avatar_key: project.avatar_key || project.handle || project.name,
          frame_style: frameStyle,
          caption: videoCaption || store.topic || "AI 영상",
          likes_count: videoLikesCount || `${Math.floor(Math.random() * 50 + 10)}K`,
        } : null;

        const finalPostCardSettings = mode === "post" && project ? {
          channel_name: project.name,
          avatar_key: project.avatar_key || project.handle || project.name,
          caption: videoCaption || store.topic || "AI 영상",
        } : null;

        if (!store.projectId || !store.groupId) {
          showToast("프로젝트/그룹을 먼저 선택해주세요", "error");
          return;
        }

        const payload = {
          project_id: store.projectId,
          group_id: store.groupId,
          storyboard_id: store.storyboardId,
          scenes: scenes
            .filter((s) => s.image_url)
            .map((s) => ({
              image_url: s.image_url,
              script: s.script,
              speaker: s.speaker,
              duration: s.duration,
            })),
          storyboard_title: store.topic || "my_shorts",
          layout_style: mode,
          ken_burns_preset: kenBurnsPreset,
          ken_burns_intensity: kenBurnsIntensity,
          transition_type: transitionType,
          include_scene_text: includeSceneText,
          scene_text_font: sceneTextFont,
          tts_engine: "qwen",
          voice_design_prompt: voiceDesignPrompt,
          voice_preset_id: voicePresetId || null,
          speed_multiplier: speedMultiplier,
          bgm_file: bgmFile,
          audio_ducking: audioDucking,
          bgm_volume: bgmVolume,
          overlay_settings: finalOverlaySettings,
          post_card_settings: finalPostCardSettings,
        };

        const res = await axios.post(`${API_BASE}/video/create`, payload);
        const url = res.data.video_url;
        if (mode === "full") {
          setOutput({ videoUrlFull: url, videoUrl: url });
        } else {
          setOutput({ videoUrlPost: url, videoUrl: url });
        }
        setOutput({
          recentVideos: [
            { url, label: mode, createdAt: Date.now() },
            ...recentVideos.slice(0, 9),
          ],
        });
        showToast("Video rendered", "success");
      } catch {
        showToast("Render failed", "error");
      } finally {
        setOutput({ isRendering: false });
      }
    },
    [scenes, store.topic, kenBurnsPreset, kenBurnsIntensity, transitionType, includeSceneText, sceneTextFont, speedMultiplier, bgmFile, audioDucking, bgmVolume, voiceDesignPrompt, voicePresetId, videoCaption, videoLikesCount, recentVideos, setOutput, showToast, frameStyle, store.projectId, store.groupId, store.storyboardId]
  );

  // ---------- BGM Preview ----------

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

  return (
    <div className="space-y-6">
      <RenderSettingsPanel
        renderPresetName={store.effectivePresetName}
        renderPresetSource={store.effectivePresetSource}
        layoutStyle={layoutStyle}
        setLayoutStyle={(v) => setOutput({ layoutStyle: v })}
        frameStyle={frameStyle}
        setFrameStyle={(v) => setOutput({ frameStyle: v })}
        canRender={canRender}
        isRendering={isRendering}
        scenesWithImages={scenes.filter((s) => !!s.image_url).length}
        totalScenes={scenes.length}
        onRender={() => handleRender(layoutStyle)}
        includeSceneText={includeSceneText}
        setIncludeSceneText={(v) => setOutput({ includeSceneText: v })}
        sceneTextFont={sceneTextFont}
        setSubtitleFont={(v) => setOutput({ sceneTextFont: v })}
        fontList={fontList}
        loadedFonts={loadedFonts}
        kenBurnsPreset={kenBurnsPreset}
        setKenBurnsPreset={(v) => setOutput({ kenBurnsPreset: v })}
        kenBurnsIntensity={kenBurnsIntensity}
        setKenBurnsIntensity={(v) => setOutput({ kenBurnsIntensity: v })}
        transitionType={transitionType}
        setTransitionType={(v) => setOutput({ transitionType: v })}
        speedMultiplier={speedMultiplier}
        setSpeedMultiplier={(v) => setOutput({ speedMultiplier: v })}
        bgmFile={bgmFile}
        setBgmFile={(v) => setOutput({ bgmFile: v })}
        bgmList={bgmList}
        onPreviewBgm={handlePreviewBgm}
        isPreviewingBgm={isPreviewingBgm}
        audioDucking={audioDucking}
        setAudioDucking={(v) => setOutput({ audioDucking: v })}
        bgmVolume={bgmVolume}
        setBgmVolume={(v) => setOutput({ bgmVolume: v })}
        voiceDesignPrompt={voiceDesignPrompt}
        setVoiceDesignPrompt={(v) => setOutput({ voiceDesignPrompt: v })}
        voicePresetId={voicePresetId}
        setVoicePresetId={(v) => setOutput({ voicePresetId: v })}
      />
    </div>
  );
}
