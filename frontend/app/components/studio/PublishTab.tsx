"use client";

import { useUIStore } from "../../store/useUIStore";
import { useContextStore } from "../../store/useContextStore";
import { RenderMediaPanel, RenderSidePanel } from "../video/RenderSettingsPanel";
import VideoPreviewHero from "../video/VideoPreviewHero";
import { PublishVideosSection, PublishCaptionLikes } from "./PublishMetaPanel";
import { usePublishRender } from "../../hooks/usePublishRender";
import { PUBLISH_2COL_LAYOUT } from "../ui/variants";

export default function PublishTab() {
  const setUI = useUIStore((s) => s.set);
  const effectivePresetName = useContextStore((s) => s.effectivePresetName);
  const effectivePresetSource = useContextStore((s) => s.effectivePresetSource);

  const {
    scenes,
    store,
    setOutput,
    canRender,
    disabledReason,
    handleRender,
    handleSetVoicePresetId,
  } = usePublishRender();

  return (
    <div className="w-full space-y-6">
      {/* Warning banner: full-width above grid */}
      {disabledReason && (
        <div className="flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4">
          <span className="text-xl">⚠</span>
          <div>
            <p className="text-sm font-semibold text-amber-800">{disabledReason}</p>
            <p className="mt-0.5 text-xs text-amber-600">
              렌더링 설정은 아래에서 미리 구성할 수 있습니다.
            </p>
          </div>
        </div>
      )}

      {/* 2-column grid: left=settings, right=preview+meta */}
      <div className={PUBLISH_2COL_LAYOUT}>
        {/* ── Left column: render settings ── */}
        <div className="space-y-6">
          <div className="rounded-2xl border border-zinc-200 bg-white p-5">
            <RenderSidePanel
              layoutStyle={store.layoutStyle}
              setLayoutStyle={(v) => setOutput({ layoutStyle: v })}
              frameStyle={store.frameStyle}
              setFrameStyle={(v) => setOutput({ frameStyle: v })}
              canRender={canRender}
              isRendering={store.isRendering}
              scenesWithImages={scenes.filter((s) => !!s.image_url).length}
              totalScenes={scenes.length}
              onRender={() => handleRender(store.layoutStyle)}
              disabledReason={disabledReason}
              renderPresetName={effectivePresetName}
              renderPresetSource={effectivePresetSource}
              renderProgress={store.renderProgress}
            />
          </div>

          <RenderMediaPanel
            includeSceneText={store.includeSceneText}
            setIncludeSceneText={(v) => setOutput({ includeSceneText: v })}
            sceneTextFont={store.sceneTextFont}
            setSceneTextFont={(v) => setOutput({ sceneTextFont: v })}
            fontList={store.fontList}
            loadedFonts={store.loadedFonts}
            kenBurnsPreset={store.kenBurnsPreset}
            setKenBurnsPreset={(v) => setOutput({ kenBurnsPreset: v })}
            kenBurnsIntensity={store.kenBurnsIntensity}
            setKenBurnsIntensity={(v) => setOutput({ kenBurnsIntensity: v })}
            transitionType={store.transitionType}
            setTransitionType={(v) => setOutput({ transitionType: v })}
            speedMultiplier={store.speedMultiplier}
            setSpeedMultiplier={(v) => setOutput({ speedMultiplier: v })}
            audioDucking={store.audioDucking}
            setAudioDucking={(v) => setOutput({ audioDucking: v })}
            bgmVolume={store.bgmVolume}
            setBgmVolume={(v) => setOutput({ bgmVolume: v })}
            voiceDesignPrompt={store.voiceDesignPrompt}
            setVoiceDesignPrompt={(v) => setOutput({ voiceDesignPrompt: v })}
            voicePresetId={store.voicePresetId}
            setVoicePresetId={handleSetVoicePresetId}
            bgmMode={store.bgmMode}
            setBgmMode={(v) => setOutput({ bgmMode: v })}
            musicPresetId={store.musicPresetId}
            setMusicPresetId={(v) => setOutput({ musicPresetId: v })}
            bgmPrompt={store.bgmPrompt}
            bgmMood={store.bgmMood}
            setBgmPrompt={(v) => setOutput({ bgmPrompt: v })}
            defaultOpen={true}
            readOnly
          />
        </div>

        {/* ── Right column: preview + meta (sticky) ── */}
        <div className="space-y-6 self-start md:sticky md:top-0">
          <VideoPreviewHero
            videoUrl={store.videoUrl}
            onClickFullscreen={(url) => setUI({ videoPreviewSrc: url })}
            compact
            isRendering={store.isRendering}
            renderProgress={store.renderProgress}
          />

          <div className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5">
            <PublishCaptionLikes />
          </div>

          <PublishVideosSection variant="list" />
        </div>
      </div>
    </div>
  );
}
