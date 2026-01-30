"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { API_BASE, VOICES } from "../../constants";
import type { SetStateAction } from "react";
import type { AudioItem, FontItem, OverlaySettings, PostCardSettings, SdModel } from "../../types";
import RenderSettingsPanel from "../video/RenderSettingsPanel";
import RenderedVideosSection from "../video/RenderedVideosSection";
import { getAvatarInitial, slugifyAvatarKey } from "../../utils";

export default function OutputTab() {
  const store = useStudioStore();
  const {
    scenes,
    layoutStyle,
    isRendering,
    includeSubtitles,
    subtitleFont,
    fontList,
    loadedFonts,
    kenBurnsPreset,
    kenBurnsIntensity,
    transitionType,
    narratorVoice,
    speedMultiplier,
    bgmFile,
    bgmList,
    audioDucking,
    bgmVolume,
    overlaySettings,
    overlayAvatarUrl,
    postCardSettings,
    postAvatarUrl,
    isRegeneratingAvatar,
    sdModels,
    currentModel,
    selectedModel,
    isModelUpdating,
    videoUrl,
    videoUrlFull,
    videoUrlPost,
    recentVideos,
    setOutput,
    showToast,
    setMeta,
  } = store;

  // Load audio and font lists on mount
  useEffect(() => {
    axios
      .get(`${API_BASE}/audio/list`)
      .then((r) => setOutput({ bgmList: r.data.audios || [] }))
      .catch(() => {});
    axios
      .get(`${API_BASE}/fonts`)
      .then((r) => setOutput({ fontList: r.data || [] }))
      .catch(() => {});
    axios
      .get(`${API_BASE}/sd/models`)
      .then((r) => setOutput({ sdModels: r.data.models || [] }))
      .catch(() => {});
  }, [setOutput]);

  const canRender = scenes.filter((s) => !!s.image_url).length > 0;

  const handleRender = useCallback(
    async (mode: "full" | "post") => {
      setOutput({ isRendering: true });
      try {
        const payload = {
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
          include_subtitles: includeSubtitles,
          subtitle_font: subtitleFont,
          narrator_voice: narratorVoice,
          speed_multiplier: speedMultiplier,
          bgm_file: bgmFile,
          audio_ducking: audioDucking,
          bgm_volume: bgmVolume,
        };
        const res = await axios.post(`${API_BASE}/video/render`, payload);
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
    [scenes, store.topic, kenBurnsPreset, kenBurnsIntensity, transitionType, includeSubtitles, subtitleFont, narratorVoice, speedMultiplier, bgmFile, audioDucking, bgmVolume, recentVideos, setOutput, showToast]
  );

  const handleDeleteRecentVideo = useCallback(
    async (url: string) => {
      try {
        const filename = url.split("/").pop();
        await axios.delete(`${API_BASE}/video`, { data: { filename } });
        setOutput({ recentVideos: recentVideos.filter((v) => v.url !== url) });
      } catch {
        showToast("Failed to delete video", "error");
      }
    },
    [recentVideos, setOutput, showToast]
  );

  return (
    <div className="space-y-6">
      <RenderSettingsPanel
        layoutStyle={layoutStyle}
        setLayoutStyle={(v) => setOutput({ layoutStyle: v })}
        canRender={canRender}
        isRendering={isRendering}
        scenesWithImages={scenes.filter((s) => !!s.image_url).length}
        totalScenes={scenes.length}
        onRender={() => handleRender(layoutStyle)}
        includeSubtitles={includeSubtitles}
        setIncludeSubtitles={(v) => setOutput({ includeSubtitles: v })}
        subtitleFont={subtitleFont}
        setSubtitleFont={(v) => setOutput({ subtitleFont: v })}
        fontList={fontList}
        loadedFonts={loadedFonts}
        kenBurnsPreset={kenBurnsPreset}
        setKenBurnsPreset={(v) => setOutput({ kenBurnsPreset: v })}
        kenBurnsIntensity={kenBurnsIntensity}
        setKenBurnsIntensity={(v) => setOutput({ kenBurnsIntensity: v })}
        transitionType={transitionType}
        setTransitionType={(v) => setOutput({ transitionType: v })}
        narratorVoice={narratorVoice}
        setNarratorVoice={(v) => setOutput({ narratorVoice: v })}
        speedMultiplier={speedMultiplier}
        setSpeedMultiplier={(v) => setOutput({ speedMultiplier: v })}
        bgmFile={bgmFile}
        setBgmFile={(v) => setOutput({ bgmFile: v })}
        bgmList={bgmList}
        onPreviewBgm={() => {}}
        isPreviewingBgm={false}
        audioDucking={audioDucking}
        setAudioDucking={(v) => setOutput({ audioDucking: v })}
        bgmVolume={bgmVolume}
        setBgmVolume={(v) => setOutput({ bgmVolume: v })}
        overlaySettings={overlaySettings}
        setOverlaySettings={((v: SetStateAction<OverlaySettings>) => {
          const next = typeof v === "function" ? v(overlaySettings) : v;
          setOutput({ overlaySettings: next });
        }) as React.Dispatch<SetStateAction<OverlaySettings>>}
        overlayAvatarUrl={overlayAvatarUrl}
        postCardSettings={postCardSettings}
        setPostCardSettings={((v: SetStateAction<PostCardSettings>) => {
          const next = typeof v === "function" ? v(postCardSettings) : v;
          setOutput({ postCardSettings: next });
        }) as React.Dispatch<SetStateAction<PostCardSettings>>}
        postAvatarUrl={postAvatarUrl}
        onAutoFillOverlay={() => {}}
        onAutoFillPostCard={() => {}}
        onRegenerateAvatar={() => {}}
        isRegeneratingAvatar={isRegeneratingAvatar}
        getAvatarInitial={getAvatarInitial}
        slugifyAvatarKey={slugifyAvatarKey}
        currentModel={currentModel}
        selectedModel={selectedModel}
        sdModels={sdModels}
        onModelChange={() => {}}
        isModelUpdating={isModelUpdating}
      />

      <RenderedVideosSection
        videoUrl={videoUrl}
        videoUrlFull={videoUrlFull}
        videoUrlPost={videoUrlPost}
        recentVideos={recentVideos}
        onVideoPreview={(src) => setMeta({ videoPreviewSrc: src })}
        onDeleteRecentVideo={handleDeleteRecentVideo}
      />
    </div>
  );
}
