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
    frameStyle,
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
    postCardSettings,
    currentStyleProfile,
    videoUrl,
    videoUrlFull,
    videoUrlPost,
    recentVideos,
    setOutput,
    showToast,
    setMeta,
    channelProfile,
    channelAvatarUrl,
    hasValidProfile,
  } = store;

  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);
  const [isPreviewingBgm, setIsPreviewingBgm] = useState(false);

  // Video-specific metadata (not in profile)
  const [videoCaption, setVideoCaption] = useState("");
  const [videoLikesCount, setVideoLikesCount] = useState("");
  const captionInitialized = useRef(false);
  const likesInitialized = useRef(false);

  // Auto-populate video metadata with smart defaults (only once)
  useEffect(() => {
    if (!captionInitialized.current && !videoCaption && store.topic) {
      setVideoCaption(store.topic);
      captionInitialized.current = true;
    }
    if (!likesInitialized.current && !videoLikesCount) {
      setVideoLikesCount(`${Math.floor(Math.random() * 50 + 10)}K`);
      likesInitialized.current = true;
    }
  }, [store.topic, videoCaption, videoLikesCount]);

  // Load audio, font, and SD model lists on mount
  useEffect(() => {
    axios
      .get(`${API_BASE}/audio/list`)
      .then((r) => setOutput({ bgmList: r.data.audios || [] }))
      .catch(() => { });
    axios
      .get(`${API_BASE}/fonts/list`)
      .then((r) => setOutput({ fontList: r.data.fonts || [] }))
      .catch(() => { });
  }, [setOutput]);

  // Cleanup audio on unmount
  useEffect(() => () => stopBgmPreview(), []);

  const canRender = scenes.filter((s) => !!s.image_url).length > 0;

  // ---------- Render ----------

  const handleRender = useCallback(
    async (mode: "full" | "post") => {
      // Check if profile is set
      if (!hasValidProfile()) {
        showToast("채널 프로필을 먼저 설정해주세요 (상단 버튼 클릭)", "error");
        return;
      }

      setOutput({ isRendering: true });
      try {
        // Build settings with profile + video metadata
        const finalOverlaySettings = mode === "full" && channelProfile ? {
          channel_name: channelProfile.channel_name,
          avatar_key: channelProfile.avatar_key,
          frame_style: frameStyle,
          caption: videoCaption || store.topic || "AI 영상",
          likes_count: videoLikesCount || `${Math.floor(Math.random() * 50 + 10)}K`,
        } : null;

        const finalPostCardSettings = mode === "post" && channelProfile ? {
          channel_name: channelProfile.channel_name,
          avatar_key: channelProfile.avatar_key,
          caption: videoCaption || store.topic || "AI 영상",
        } : null;

        const payload = {
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
          include_subtitles: includeSubtitles,
          subtitle_font: subtitleFont,
          narrator_voice: narratorVoice,
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
    [scenes, store.topic, kenBurnsPreset, kenBurnsIntensity, transitionType, includeSubtitles, subtitleFont, narratorVoice, speedMultiplier, bgmFile, audioDucking, bgmVolume, channelProfile, hasValidProfile, videoCaption, videoLikesCount, recentVideos, setOutput, showToast]
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

  return (
    <div className="space-y-6">
      {/* Channel Profile Section */}
      {channelProfile ? (
        <div className="rounded-2xl border border-zinc-200 bg-white p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-zinc-800">채널 프로필</h3>
            <p className="text-xs text-zinc-400">상단 버튼으로 변경 가능</p>
          </div>
          <div className="flex items-center gap-3 rounded-xl border border-zinc-100 bg-zinc-50 p-3">
            <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-full border-2 border-white shadow-sm bg-zinc-100 text-sm font-semibold text-zinc-600">
              {channelAvatarUrl ? (
                <img
                  src={channelAvatarUrl}
                  alt={channelProfile.channel_name}
                  className="h-full w-full object-cover"
                />
              ) : (
                getAvatarInitial(channelProfile.channel_name)
              )}
            </div>
            <div className="flex-1">
              <p className="font-semibold text-sm text-zinc-800">{channelProfile.channel_name}</p>
              <p className="text-xs text-zinc-500">@{channelProfile.avatar_key}</p>
            </div>
          </div>

          {/* Video-specific Metadata */}
          <div className="mt-4 space-y-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-zinc-600">
                  캡션 (이 영상) <span className="text-red-500">*</span>
                </label>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${videoCaption.length >= 60 ? 'bg-red-100 text-red-600' :
                  videoCaption.length >= 50 ? 'bg-amber-100 text-amber-600' :
                    'text-zinc-400'
                  }`}>
                  {videoCaption.length}/60
                </span>
              </div>
              <input
                type="text"
                value={videoCaption}
                onChange={(e) => setVideoCaption(e.target.value.slice(0, 60))}
                placeholder={`예: ${store.topic || "AI 생성 영상"}`}
                maxLength={60}
                className={`w-full rounded-xl border px-3 py-2 text-sm outline-none focus:ring-2 transition-colors ${videoCaption.length >= 60
                  ? 'border-red-300 focus:border-red-400 focus:ring-red-50 bg-red-50/30'
                  : videoCaption.length >= 50
                    ? 'border-amber-300 focus:border-amber-400 focus:ring-amber-50 bg-amber-50/30'
                    : 'border-zinc-200 focus:border-indigo-400 focus:ring-indigo-50'
                  }`}
              />
              <div className="flex items-start gap-1 mt-1">
                {videoCaption.length >= 60 ? (
                  <p className="text-[10px] text-red-600 font-medium">
                    ⚠️ 최대 60자 제한 (가로폭 초과 시 잘림)
                  </p>
                ) : videoCaption.length >= 50 ? (
                  <p className="text-[10px] text-amber-600 font-medium">
                    ⚡ 50자 초과 - 간결하게 작성 권장
                  </p>
                ) : videoCaption ? (
                  <p className="text-[10px] text-zinc-400">
                    ✓ 가로폭 고려하여 60자 이내 권장
                  </p>
                ) : (
                  <p className="text-[10px] text-zinc-400">
                    비워두면 스토리보드 주제가 사용됩니다
                  </p>
                )}
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-zinc-600 mb-1">
                좋아요 수 (선택)
              </label>
              <input
                type="text"
                value={videoLikesCount}
                onChange={(e) => setVideoLikesCount(e.target.value)}
                placeholder="예: 1.2K (비워두면 랜덤)"
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-50"
              />
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border-2 border-dashed border-amber-200 bg-amber-50 p-6 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-amber-100 mb-3">
            <span className="text-2xl">⚠️</span>
          </div>
          <h3 className="text-sm font-bold text-amber-800 mb-2">채널 프로필 설정 필요</h3>
          <p className="text-xs text-amber-600">
            상단 TabBar의 "⚠️ 채널 설정" 버튼을 클릭하세요
          </p>
        </div>
      )}

      <RenderSettingsPanel
        layoutStyle={layoutStyle}
        setLayoutStyle={(v) => setOutput({ layoutStyle: v })}
        frameStyle={frameStyle}
        setFrameStyle={(v) => setOutput({ frameStyle: v })}
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
        currentStyleProfile={currentStyleProfile}
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
