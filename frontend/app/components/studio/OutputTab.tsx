"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { API_BASE } from "../../constants";
import type { SetStateAction } from "react";
import type { AudioItem, FontItem, OverlaySettings, PostCardSettings, SdModel } from "../../types";
import RenderSettingsPanel from "../video/RenderSettingsPanel";
import RenderedVideosSection from "../video/RenderedVideosSection";
import {
  slugifyAvatarKey,
  applyHeartPrefix,
  generateChannelName,
} from "../../utils";
import { createGroup } from "../../store/actions/groupActions";
import { updateStoryboardMetadata } from "../../store/actions/storyboardActions";
import { getCurrentProject, hasValidProfile } from "../../store/selectors/projectSelectors";

export default function OutputTab() {
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
    overlaySettings,
    postCardSettings,
    voiceDesignPrompt,
    voiceRefAudioUrl,
    voicePresetId,
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

  // Video-specific metadata (from store for persistence)
  const videoCaption = useStudioStore((state) => state.videoCaption);
  const videoLikesCount = useStudioStore((state) => state.videoLikesCount);
  const captionInitialized = useRef(false);
  const [isExtractingCaption, setIsExtractingCaption] = useState(false);
  const likesInitialized = useRef(false);

  // Auto-populate video metadata with smart defaults (only once)
  useEffect(() => {
    if (!captionInitialized.current && !videoCaption && store.topic) {
      setOutput({ videoCaption: store.topic });
      captionInitialized.current = true;
    }
    if (!likesInitialized.current && !videoLikesCount) {
      setOutput({ videoLikesCount: `${Math.floor(Math.random() * 50 + 10)}K` });
      likesInitialized.current = true;
    }
  }, [store.topic, videoCaption, videoLikesCount, setOutput]);

  // Extract caption using LLM
  const handleExtractCaption = async () => {
    if (!videoCaption || videoCaption.length <= 60) {
      showToast("캡션이 이미 60자 이내입니다", "success");
      return;
    }

    setIsExtractingCaption(true);
    try {
      const res = await axios.post(`${API_BASE}/video/extract-caption`, {
        text: videoCaption
      });

      if (res.data.caption) {
        setOutput({ videoCaption: res.data.caption });
        // Persist to DB immediately
        updateStoryboardMetadata({ default_caption: res.data.caption });
        showToast(
          res.data.fallback
            ? "캡션을 잘라냈습니다"
            : `캡션 요약 완료 (${res.data.original_length} → ${res.data.caption.length}자)`,
          "success"
        );
      }
    } catch (err: any) {
      console.error("Caption extraction failed:", err);
      showToast(err.response?.data?.detail || "캡션 요약 실패", "error");
    } finally {
      setIsExtractingCaption(false);
    }
  };

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
      // Check if project is selected
      if (!hasValidProfile()) {
        showToast("프로젝트를 먼저 선택해주세요", "error");
        return;
      }

      setOutput({ isRendering: true });
      try {
        // Build settings with project-based channel info
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
          voice_ref_audio_url: voiceRefAudioUrl,
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
    [scenes, store.topic, kenBurnsPreset, kenBurnsIntensity, transitionType, includeSceneText, sceneTextFont, speedMultiplier, bgmFile, audioDucking, bgmVolume, voiceDesignPrompt, voiceRefAudioUrl, voicePresetId, videoCaption, videoLikesCount, recentVideos, setOutput, showToast]
  );

  const handleDeleteRecentVideo = useCallback(
    async (url: string) => {
      try {
        const filename = url.split("/").pop();
        if (!filename) {
          showToast("Invalid video URL", "error");
          return;
        }

        await axios.post(`${API_BASE}/video/delete`, { filename });

        // Filter by filename instead of full URL (more reliable)
        setOutput({
          recentVideos: recentVideos.filter((v) => {
            const vFilename = v.url.split("/").pop();
            return vFilename !== filename;
          })
        });

        showToast("Video deleted successfully", "success");
      } catch (error) {
        console.error("Delete failed:", error);
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
      {/* Video Metadata */}
      <div className="rounded-2xl border border-zinc-200 bg-white p-4 space-y-3">
        <h3 className="text-sm font-bold text-zinc-800">영상 메타데이터</h3>
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-semibold text-zinc-600">
              캡션 (이 영상) <span className="text-red-500">*</span>
            </label>
            <div className="flex items-center gap-2">
              {videoCaption.length > 60 && (
                <button
                  onClick={handleExtractCaption}
                  disabled={isExtractingCaption}
                  className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-100 text-indigo-600 hover:bg-indigo-200 disabled:opacity-50 transition-colors"
                  title="LLM으로 캡션 요약"
                >
                  {isExtractingCaption ? "..." : "요약"}
                </button>
              )}
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${videoCaption.length >= 60 ? 'bg-red-100 text-red-600' :
                videoCaption.length >= 50 ? 'bg-amber-100 text-amber-600' :
                  'text-zinc-400'
                }`}>
                {videoCaption.length}/60
              </span>
            </div>
          </div>
          <input
            type="text"
            value={videoCaption}
            onChange={(e) => setOutput({ videoCaption: e.target.value })}
            onBlur={(e) => updateStoryboardMetadata({ default_caption: e.target.value })}
            placeholder={`예: ${store.topic || "AI 생성 영상"}`}
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
                최대 60자 제한 (가로폭 초과 시 잘림)
              </p>
            ) : videoCaption.length >= 50 ? (
              <p className="text-[10px] text-amber-600 font-medium">
                50자 초과 - 간결하게 작성 권장
              </p>
            ) : videoCaption ? (
              <p className="text-[10px] text-zinc-400">
                가로폭 고려하여 60자 이내 권장
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
            onChange={(e) => setOutput({ videoLikesCount: e.target.value })}
            placeholder="예: 1.2K (비워두면 랜덤)"
            className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-50"
          />
        </div>
      </div>

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
        voiceRefAudioUrl={voiceRefAudioUrl}
        setVoiceRefAudioUrl={(v) => setOutput({ voiceRefAudioUrl: v })}
        voicePresetId={voicePresetId}
        setVoicePresetId={(v) => setOutput({ voicePresetId: v })}
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
