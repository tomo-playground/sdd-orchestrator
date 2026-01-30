"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { API_BASE, VOICES } from "../../constants";
import type { SetStateAction } from "react";
import type { AudioItem, FontItem, OverlaySettings, PostCardSettings, SdModel } from "../../types";
import RenderSettingsPanel from "../video/RenderSettingsPanel";
import RenderedVideosSection from "../video/RenderedVideosSection";
import {
  getAvatarInitial,
  slugifyAvatarKey,
  applyHeartPrefix,
  generateChannelName,
} from "../../utils";

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

  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);
  const [isPreviewingBgm, setIsPreviewingBgm] = useState(false);

  // Load audio, font, and SD model lists on mount
  useEffect(() => {
    axios
      .get(`${API_BASE}/audio/list`)
      .then((r) => setOutput({ bgmList: r.data.audios || [] }))
      .catch(() => {});
    axios
      .get(`${API_BASE}/fonts/list`)
      .then((r) => setOutput({ fontList: r.data.fonts || [] }))
      .catch(() => {});
    axios
      .get(`${API_BASE}/sd/models`)
      .then((r) => setOutput({ sdModels: r.data.models || [] }))
      .catch(() => {});
  }, [setOutput]);

  // Resolve avatar previews when keys change
  useEffect(() => {
    resolveAvatarPreview(overlaySettings.avatar_key ?? "", "overlay");
  }, [overlaySettings.avatar_key]);

  useEffect(() => {
    resolveAvatarPreview(postCardSettings.avatar_key ?? "", "post");
  }, [postCardSettings.avatar_key]);

  // Cleanup audio on unmount
  useEffect(() => () => stopBgmPreview(), []);

  const canRender = scenes.filter((s) => !!s.image_url).length > 0;

  // ---------- Render ----------

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
          overlay_settings: mode === "full" ? overlaySettings : null,
          post_card_settings: mode === "post" ? postCardSettings : null,
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
    [scenes, store.topic, kenBurnsPreset, kenBurnsIntensity, transitionType, includeSubtitles, subtitleFont, narratorVoice, speedMultiplier, bgmFile, audioDucking, bgmVolume, overlaySettings, postCardSettings, recentVideos, setOutput, showToast]
  );

  const handleDeleteRecentVideo = useCallback(
    async (url: string) => {
      try {
        const filename = url.split("/").pop();
        await axios.post(`${API_BASE}/video/delete`, { filename });
        setOutput({ recentVideos: recentVideos.filter((v) => v.url !== url) });
      } catch {
        showToast("Failed to delete video", "error");
      }
    },
    [recentVideos, setOutput, showToast]
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

  // ---------- Auto-fill Overlay / PostCard ----------

  function buildOverlayContext() {
    const fallbackProfile = generateChannelName(store.topic);
    const scripts = scenes.map((s) => s.script.trim()).filter(Boolean);
    const baseCaption = scripts[0] || store.topic.trim() || "Today's shorts";
    const hashtagSource = (store.topic || baseCaption).split(/\s+/).slice(0, 2);
    const hashtags = hashtagSource
      .map((t) => t.replace(/[^\w가-힣]/g, ""))
      .filter(Boolean)
      .map((t) => `#${t}`);
    const caption = applyHeartPrefix(hashtags.join(" "));
    const likesPool = ["1.2k", "3.8k", "7.4k", "12.5k", "18.9k"];
    const likes_count = likesPool[baseCaption.length % likesPool.length];
    return {
      channel_name: fallbackProfile,
      avatar_key: slugifyAvatarKey(fallbackProfile),
      likes_count,
      caption,
    };
  }

  function handleAutoFillOverlay() {
    const auto = buildOverlayContext();
    setOutput({ overlaySettings: { ...overlaySettings, ...auto } });
  }

  function handleAutoFillPostCard() {
    const auto = buildOverlayContext();
    setOutput({
      postCardSettings: {
        ...postCardSettings,
        channel_name: auto.channel_name,
        avatar_key: auto.avatar_key,
        caption: auto.caption,
      },
    });
  }

  // ---------- Avatar ----------

  async function resolveAvatarPreview(avatarKey: string, target: "overlay" | "post") {
    const trimmed = avatarKey.trim();
    if (!trimmed) {
      setOutput(target === "overlay" ? { overlayAvatarUrl: null } : { postAvatarUrl: null });
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/avatar/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ avatar_key: trimmed }),
      });
      if (!res.ok) {
        setOutput(target === "overlay" ? { overlayAvatarUrl: null } : { postAvatarUrl: null });
        return;
      }
      const data = await res.json();
      if (data?.filename) {
        const url = `${API_BASE}/outputs/avatars/${data.filename}?t=${Date.now()}`;
        setOutput(target === "overlay" ? { overlayAvatarUrl: url } : { postAvatarUrl: url });
      }
    } catch {
      // ignore
    }
  }

  async function handleRegenerateAvatar(avatarKey: string) {
    const trimmed = avatarKey.trim();
    if (!trimmed) return;
    setOutput({ isRegeneratingAvatar: true });
    try {
      const res = await fetch(`${API_BASE}/avatar/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ avatar_key: trimmed }),
      });
      if (!res.ok) throw new Error("Avatar regenerate failed");
      const data = await res.json();
      if (data?.filename) {
        const url = `${API_BASE}/outputs/avatars/${data.filename}?t=${Date.now()}`;
        if (trimmed === overlaySettings.avatar_key?.trim()) {
          setOutput({ overlayAvatarUrl: url });
        }
        if (trimmed === postCardSettings.avatar_key?.trim()) {
          setOutput({ postAvatarUrl: url });
        }
      }
    } catch {
      showToast("Avatar regeneration failed", "error");
    } finally {
      setOutput({ isRegeneratingAvatar: false });
    }
  }

  // ---------- SD Model ----------

  async function handleModelChange(value: string) {
    if (!value) return;
    setOutput({ selectedModel: value, isModelUpdating: true });
    try {
      const res = await axios.post(`${API_BASE}/sd/options`, {
        sd_model_checkpoint: value,
      });
      setOutput({ currentModel: res.data.model || value });
    } catch {
      showToast("Model update failed", "error");
      setOutput({ selectedModel: currentModel });
    } finally {
      setOutput({ isModelUpdating: false });
    }
  }

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
        onPreviewBgm={handlePreviewBgm}
        isPreviewingBgm={isPreviewingBgm}
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
        onAutoFillOverlay={handleAutoFillOverlay}
        onAutoFillPostCard={handleAutoFillPostCard}
        onRegenerateAvatar={handleRegenerateAvatar}
        isRegeneratingAvatar={isRegeneratingAvatar}
        getAvatarInitial={getAvatarInitial}
        slugifyAvatarKey={slugifyAvatarKey}
        currentModel={currentModel}
        selectedModel={selectedModel}
        sdModels={sdModels}
        onModelChange={handleModelChange}
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
