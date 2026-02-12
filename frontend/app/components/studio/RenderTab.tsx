"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useRenderStore } from "../../store/useRenderStore";
import { useContextStore } from "../../store/useContextStore";
import { useUIStore } from "../../store/useUIStore";
import { API_BASE } from "../../constants";
import { RenderMediaPanel, RenderSidePanel } from "../video/RenderSettingsPanel";
import { getCurrentProject, hasValidProfile } from "../../store/selectors/projectSelectors";
import { SIDE_PANEL_LAYOUT } from "../ui/variants";
import { renderWithProgress } from "../../utils/renderWithProgress";
import { getErrorMsg } from "../../utils/error";

export default function RenderTab() {
  const scenes = useStoryboardStore((s) => s.scenes);
  const topic = useStoryboardStore((s) => s.topic);

  const {
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
    bgmMode,
    musicPresetId,
    recentVideos,
    renderProgress,
  } = useRenderStore();

  const setOutput = useRenderStore((s) => s.set);
  const showToast = useUIStore((s) => s.showToast);
  const videoCaption = useRenderStore((s) => s.videoCaption);
  const videoLikesCount = useRenderStore((s) => s.videoLikesCount);

  const projectId = useContextStore((s) => s.projectId);
  const groupId = useContextStore((s) => s.groupId);
  const storyboardId = useContextStore((s) => s.storyboardId);
  const effectivePresetName = useContextStore((s) => s.effectivePresetName);
  const effectivePresetSource = useContextStore((s) => s.effectivePresetSource);

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
        // Mark as loaded to stop "Loading..." spinner, fallback to sans-serif
        setOutput({ loadedFonts: new Set([...loadedFonts, sceneTextFont]) });
      });
  }, [sceneTextFont, loadedFonts, setOutput]);

  // Cleanup audio on unmount
  useEffect(() => () => stopBgmPreview(), []);

  const canRender = scenes.filter((s) => !!s.image_url).length > 0;

  const getDisabledReason = (): string | null => {
    if (scenes.length === 0) return "스토리보드를 먼저 생성하세요";
    if (!hasValidProfile()) return "프로젝트를 먼저 선택하세요";
    if (scenes.filter((s) => !!s.image_url).length === 0) return "이미지가 있는 씬이 필요합니다";
    return null;
  };
  const disabledReason = getDisabledReason();

  // ---------- Render ----------

  const handleRender = useCallback(
    async (mode: "full" | "post") => {
      if (!hasValidProfile()) {
        showToast("프로젝트를 먼저 선택해주세요", "error");
        return;
      }

      setOutput({ isRendering: true, renderProgress: null });
      try {
        const project = getCurrentProject();
        const finalOverlaySettings =
          mode === "full" && project
            ? {
                channel_name: project.name,
                avatar_key: project.avatar_key || project.handle || project.name,
                frame_style: frameStyle,
                caption: videoCaption,
                likes_count: videoLikesCount,
              }
            : null;

        const finalPostCardSettings =
          mode === "post" && project
            ? {
                channel_name: project.name,
                avatar_key: project.avatar_key || project.handle || project.name,
                caption: videoCaption,
              }
            : null;

        if (!projectId || !groupId) {
          showToast("프로젝트/그룹을 먼저 선택해주세요", "error");
          return;
        }
        const hasDataUrl = scenes.some((s) => s.image_url?.startsWith("data:"));
        if (hasDataUrl) {
          showToast("이미지를 저장한 뒤 렌더해주세요 (data URL은 전송할 수 없습니다)", "error");
          setOutput({ isRendering: false });
          return;
        }

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
          bgm_mode: bgmMode,
          music_preset_id: musicPresetId || null,
          audio_ducking: audioDucking,
          bgm_volume: bgmVolume,
          overlay_settings: finalOverlaySettings,
          post_card_settings: finalPostCardSettings,
        };

        const result = await renderWithProgress(payload, (p) => {
          setOutput({ renderProgress: p });
        });

        const url = result.video_url;
        if (url) {
          if (mode === "full") {
            setOutput({ videoUrlFull: url, videoUrl: url });
          } else {
            setOutput({ videoUrlPost: url, videoUrl: url });
          }
          setOutput({
            recentVideos: [
              {
                url,
                label: mode,
                createdAt: Date.now(),
                renderHistoryId: result.render_history_id,
              },
              ...recentVideos.slice(0, 9),
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
    [
      scenes,
      topic,
      kenBurnsPreset,
      kenBurnsIntensity,
      transitionType,
      includeSceneText,
      sceneTextFont,
      speedMultiplier,
      bgmFile,
      bgmMode,
      musicPresetId,
      audioDucking,
      bgmVolume,
      voiceDesignPrompt,
      voicePresetId,
      videoCaption,
      videoLikesCount,
      recentVideos,
      setOutput,
      showToast,
      frameStyle,
      projectId,
      groupId,
      storyboardId,
    ]
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
    <div className={SIDE_PANEL_LAYOUT}>
      {/* Left: Media Settings */}
      {disabledReason && (
        <div className="col-span-full mb-2 flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4">
          <span className="text-xl">⚠</span>
          <div>
            <p className="text-sm font-semibold text-amber-800">{disabledReason}</p>
            <p className="mt-0.5 text-xs text-amber-600">
              렌더링 설정은 아래에서 미리 구성할 수 있습니다.
            </p>
          </div>
        </div>
      )}
      <RenderMediaPanel
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
        setVoicePresetId={async (v) => {
          setOutput({ voicePresetId: v });
          // Persist to Group Config
          if (groupId) {
            try {
              await axios.put(`${API_BASE}/groups/${groupId}/config`, {
                narrator_voice_preset_id: v,
              });
            } catch (err) {
              console.error("[setVoicePresetId] Failed to update group config:", err);
            }
          }
        }}
        bgmMode={bgmMode}
        setBgmMode={(v) => setOutput({ bgmMode: v })}
        musicPresetId={musicPresetId}
        setMusicPresetId={(v) => setOutput({ musicPresetId: v })}
      />

      {/* Right: Layout + Render Action (sticky) */}
      <RenderSidePanel
        layoutStyle={layoutStyle}
        setLayoutStyle={(v) => setOutput({ layoutStyle: v })}
        frameStyle={frameStyle}
        setFrameStyle={(v) => setOutput({ frameStyle: v })}
        canRender={canRender}
        isRendering={isRendering}
        scenesWithImages={scenes.filter((s) => !!s.image_url).length}
        totalScenes={scenes.length}
        onRender={() => handleRender(layoutStyle)}
        disabledReason={disabledReason}
        renderPresetName={effectivePresetName}
        renderPresetSource={effectivePresetSource}
        renderProgress={renderProgress}
      />
    </div>
  );
}
