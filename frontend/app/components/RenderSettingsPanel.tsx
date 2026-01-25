"use client";

import type { AudioItem, FontItem, OverlaySettings, PostCardSettings, SdModel } from "../types";
import { VOICES } from "../constants";

type RenderSettingsPanelProps = {
  // Layout
  layoutStyle: "full" | "post";
  setLayoutStyle: (value: "full" | "post") => void;
  // Render Actions
  canRender: boolean;
  isRendering: boolean;
  scenesWithImages: number;
  totalScenes: number;
  onRender: () => void;
  // Video Settings
  includeSubtitles: boolean;
  setIncludeSubtitles: (value: boolean) => void;
  subtitleFont: string;
  setSubtitleFont: (value: string) => void;
  fontList: FontItem[];
  loadedFonts: Set<string>;
  motionStyle: "none" | "slow_zoom";
  setMotionStyle: (value: "none" | "slow_zoom") => void;
  // Audio Settings
  narratorVoice: string;
  setNarratorVoice: (value: string) => void;
  speedMultiplier: number;
  setSpeedMultiplier: (value: number) => void;
  bgmFile: string | null;
  setBgmFile: (value: string | null) => void;
  bgmList: AudioItem[];
  onPreviewBgm: () => void;
  isPreviewingBgm: boolean;
  audioDucking: boolean;
  setAudioDucking: (value: boolean) => void;
  bgmVolume: number;
  setBgmVolume: (value: number) => void;
  // Overlay / Post Card Settings
  overlaySettings: OverlaySettings;
  setOverlaySettings: React.Dispatch<React.SetStateAction<OverlaySettings>>;
  overlayAvatarUrl: string | null;
  postCardSettings: PostCardSettings;
  setPostCardSettings: React.Dispatch<React.SetStateAction<PostCardSettings>>;
  postAvatarUrl: string | null;
  onAutoFillOverlay: () => void;
  onAutoFillPostCard: () => void;
  onRegenerateAvatar: (avatarKey: string) => void;
  isRegeneratingAvatar: boolean;
  getAvatarInitial: (name: string) => string;
  slugifyAvatarKey: (name: string) => string;
  // Advanced
  currentModel: string;
  selectedModel: string;
  sdModels: SdModel[];
  onModelChange: (model: string) => void;
  isModelUpdating: boolean;
};

export default function RenderSettingsPanel({
  layoutStyle,
  setLayoutStyle,
  canRender,
  isRendering,
  scenesWithImages,
  totalScenes,
  onRender,
  includeSubtitles,
  setIncludeSubtitles,
  subtitleFont,
  setSubtitleFont,
  fontList,
  loadedFonts,
  motionStyle,
  setMotionStyle,
  narratorVoice,
  setNarratorVoice,
  speedMultiplier,
  setSpeedMultiplier,
  bgmFile,
  setBgmFile,
  bgmList,
  onPreviewBgm,
  isPreviewingBgm,
  audioDucking,
  setAudioDucking,
  bgmVolume,
  setBgmVolume,
  overlaySettings,
  setOverlaySettings,
  overlayAvatarUrl,
  postCardSettings,
  setPostCardSettings,
  postAvatarUrl,
  onAutoFillOverlay,
  onAutoFillPostCard,
  onRegenerateAvatar,
  isRegeneratingAvatar,
  getAvatarInitial,
  slugifyAvatarKey,
  currentModel,
  selectedModel,
  sdModels,
  onModelChange,
  isModelUpdating,
}: RenderSettingsPanelProps) {
  return (
    <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/70 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">Render Settings</h2>
          <p className="text-xs text-zinc-500">Configure layout, audio, and rendering.</p>
        </div>
      </div>

      {/* 1. LAYOUT + RENDER (Compact) */}
      <div className="flex flex-col items-center gap-4 rounded-2xl border-2 border-zinc-200 bg-gradient-to-r from-zinc-50 to-white p-5">
        <div className="flex items-center gap-4">
          <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Layout</span>
          <div className="flex rounded-full border border-zinc-200 bg-white p-1">
            <button
              type="button"
              onClick={() => setLayoutStyle("full")}
              className={`rounded-full px-4 py-1.5 text-xs font-medium transition ${
                layoutStyle === "full"
                  ? "bg-zinc-900 text-white"
                  : "text-zinc-500 hover:text-zinc-700"
              }`}
            >
              Full 9:16
            </button>
            <button
              type="button"
              onClick={() => setLayoutStyle("post")}
              className={`rounded-full px-4 py-1.5 text-xs font-medium transition ${
                layoutStyle === "post"
                  ? "bg-zinc-900 text-white"
                  : "text-zinc-500 hover:text-zinc-700"
              }`}
            >
              Post 1:1
            </button>
          </div>
        </div>
        <button
          onClick={onRender}
          disabled={!canRender || isRendering}
          className="rounded-full bg-zinc-900 px-10 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isRendering ? "Rendering..." : "Render"}
        </button>
        <span className="text-[10px] text-zinc-400">
          Images: {scenesWithImages}/{totalScenes}
        </span>
        {!canRender && totalScenes > 0 && (
          <p className="text-xs text-rose-500">Upload images for every scene to enable rendering.</p>
        )}
      </div>

      {/* 2. MEDIA SETTINGS (Video + Audio Combined, Collapsed by default) */}
      <details className="group rounded-2xl border border-zinc-200 bg-white/80">
        <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
          Media Settings
          <span className="text-zinc-400 transition group-open:rotate-180">▼</span>
        </summary>
        <div className="grid gap-4 border-t border-zinc-100 p-4">
          {/* Video Row */}
          <div className="grid gap-3 md:grid-cols-4">
            <label className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs font-medium text-zinc-600">
              Subtitles
              <input
                type="checkbox"
                checked={includeSubtitles}
                onChange={(e) => setIncludeSubtitles(e.target.checked)}
                className="h-4 w-4 accent-zinc-900"
              />
            </label>
            <select
              value={subtitleFont ?? ""}
              onChange={(e) => setSubtitleFont(e.target.value)}
              title="Subtitle Font"
              className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
            >
              {fontList.length === 0 && <option value="">Default</option>}
              {fontList.map((font) => (
                <option key={font.name} value={font.name}>{font.name}</option>
              ))}
            </select>
            <select
              value={motionStyle}
              onChange={(e) => setMotionStyle(e.target.value as "none" | "slow_zoom")}
              title="Effects"
              className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
            >
              <option value="none">Effects: None</option>
              <option value="slow_zoom">Effects: Slow Zoom</option>
            </select>
            <div
              className="rounded-xl border border-zinc-200 bg-zinc-900 px-3 py-2 text-center text-white text-sm"
              style={{ fontFamily: `"${subtitleFont}", sans-serif` }}
            >
              {loadedFonts.has(subtitleFont) ? "가나다" : "..."}
            </div>
          </div>
          {/* Audio Row */}
          <div className="grid gap-3 md:grid-cols-4">
            <select
              value={narratorVoice}
              onChange={(e) => setNarratorVoice(e.target.value)}
              title="Voice"
              className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
            >
              {VOICES.map((voice) => (
                <option key={voice.id} value={voice.id}>{voice.label}</option>
              ))}
            </select>
            <div className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-3 py-2">
              <span className="text-[10px] text-zinc-500">{speedMultiplier.toFixed(2)}x</span>
              <input
                type="range"
                min={0.8}
                max={1.5}
                step={0.05}
                value={speedMultiplier}
                onChange={(e) => setSpeedMultiplier(Number(e.target.value))}
                className="flex-1 accent-zinc-900"
              />
            </div>
            <div className="flex items-center gap-1">
              <select
                value={bgmFile ?? ""}
                onChange={(e) => setBgmFile(e.target.value || null)}
                title="BGM"
                className="flex-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
              >
                <option value="">BGM: None</option>
                {bgmList.map((bgm) => (
                  <option key={bgm.name} value={bgm.name}>{bgm.name}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={onPreviewBgm}
                disabled={!bgmFile || isPreviewingBgm}
                className="rounded-full border border-zinc-200 bg-white px-2 py-2 text-[10px] text-zinc-600 disabled:text-zinc-400"
              >
                ▶
              </button>
            </div>
            {bgmFile ? (
              <div className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-3 py-2">
                <span className="text-[10px] text-zinc-500">{Math.round(bgmVolume * 100)}%</span>
                <input
                  type="range"
                  min={0.05}
                  max={0.5}
                  step={0.05}
                  value={bgmVolume}
                  onChange={(e) => setBgmVolume(Number(e.target.value))}
                  className="flex-1 accent-zinc-900"
                />
                <label className="flex items-center gap-1 text-[10px] text-zinc-500">
                  <input
                    type="checkbox"
                    checked={audioDucking}
                    onChange={(e) => setAudioDucking(e.target.checked)}
                    className="h-3 w-3 accent-zinc-900"
                  />
                  Duck
                </label>
              </div>
            ) : (
              <div />
            )}
          </div>
        </div>
      </details>

      {/* 3. OVERLAY / POST CARD (Collapsible) */}
      <details className="group rounded-2xl border border-zinc-200 bg-white/80">
        <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
          {layoutStyle === "full" ? "SNS Overlay" : "Post Card Meta"}
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center overflow-hidden rounded-full border border-zinc-200 bg-white text-[10px] font-semibold text-zinc-600">
              {layoutStyle === "full" ? (
                overlayAvatarUrl ? (
                  <img src={overlayAvatarUrl} alt="Avatar" className="h-full w-full object-cover" />
                ) : (
                  getAvatarInitial(overlaySettings.channel_name ?? "")
                )
              ) : postAvatarUrl ? (
                <img src={postAvatarUrl} alt="Avatar" className="h-full w-full object-cover" />
              ) : (
                getAvatarInitial(postCardSettings.channel_name ?? "")
              )}
            </div>
            <span className="text-zinc-400 transition group-open:rotate-180">▼</span>
          </div>
        </summary>
        <div className="border-t border-zinc-100 p-4">
          {layoutStyle === "full" ? (
            <div className="grid gap-4">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={onAutoFillOverlay}
                  className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 text-[10px] font-semibold text-zinc-600 transition hover:bg-zinc-50"
                >
                  Auto Fill
                </button>
                <button
                  type="button"
                  onClick={() => onRegenerateAvatar(overlaySettings.avatar_key ?? "")}
                  disabled={isRegeneratingAvatar || !(overlaySettings.avatar_key ?? "").trim()}
                  className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 text-[10px] font-semibold text-zinc-600 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:text-zinc-400"
                >
                  {isRegeneratingAvatar ? "Regenerating..." : "Regenerate Avatar"}
                </button>
              </div>
              <input type="hidden" value={overlaySettings.frame_style} />
              <div className="grid gap-3 md:grid-cols-4">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Channel</label>
                  <input
                    value={overlaySettings.channel_name ?? ""}
                    onChange={(e) =>
                      setOverlaySettings((prev) => ({
                        ...prev,
                        channel_name: e.target.value,
                        avatar_key:
                          !prev.avatar_key || prev.avatar_key === slugifyAvatarKey(prev.channel_name)
                            ? slugifyAvatarKey(e.target.value)
                            : prev.avatar_key,
                      }))
                    }
                    className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Avatar Key</label>
                  <input
                    value={overlaySettings.avatar_key ?? ""}
                    onChange={(e) => setOverlaySettings((prev) => ({ ...prev, avatar_key: e.target.value }))}
                    className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Likes</label>
                  <input
                    value={overlaySettings.likes_count ?? ""}
                    onChange={(e) => setOverlaySettings((prev) => ({ ...prev, likes_count: e.target.value }))}
                    className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Caption</label>
                  <input
                    value={overlaySettings.caption ?? ""}
                    onChange={(e) => setOverlaySettings((prev) => ({ ...prev, caption: e.target.value }))}
                    className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="grid gap-4">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={onAutoFillPostCard}
                  className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 text-[10px] font-semibold text-zinc-600 transition hover:bg-zinc-50"
                >
                  Auto Fill
                </button>
                <button
                  type="button"
                  onClick={() => onRegenerateAvatar(postCardSettings.avatar_key ?? "")}
                  disabled={isRegeneratingAvatar || !(postCardSettings.avatar_key ?? "").trim()}
                  className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 text-[10px] font-semibold text-zinc-600 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:text-zinc-400"
                >
                  {isRegeneratingAvatar ? "Regenerating..." : "Regenerate Avatar"}
                </button>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Channel</label>
                  <input
                    value={postCardSettings.channel_name ?? ""}
                    onChange={(e) =>
                      setPostCardSettings((prev) => ({
                        ...prev,
                        channel_name: e.target.value,
                        avatar_key:
                          !prev.avatar_key || prev.avatar_key === slugifyAvatarKey(prev.channel_name)
                            ? slugifyAvatarKey(e.target.value)
                            : prev.avatar_key,
                      }))
                    }
                    className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Avatar Key</label>
                  <input
                    value={postCardSettings.avatar_key ?? ""}
                    onChange={(e) => setPostCardSettings((prev) => ({ ...prev, avatar_key: e.target.value }))}
                    className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Caption</label>
                  <input
                    value={postCardSettings.caption ?? ""}
                    onChange={(e) => setPostCardSettings((prev) => ({ ...prev, caption: e.target.value }))}
                    className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </details>

      {/* 4. ADVANCED (Collapsible - SD Model) */}
      <details className="group rounded-2xl border border-zinc-200 bg-white/80">
        <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
          Advanced
          <span className="text-zinc-400 transition group-open:rotate-180">▼</span>
        </summary>
        <div className="border-t border-zinc-100 p-4">
          <div className="flex items-center gap-3">
            <span className="text-xs text-zinc-500 whitespace-nowrap">SD Model</span>
            {isModelUpdating && <span className="text-[10px] text-zinc-400">Updating...</span>}
            <select
              value={selectedModel}
              onChange={(e) => onModelChange(e.target.value)}
              disabled={isModelUpdating || sdModels.length === 0}
              className="flex-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400 disabled:bg-zinc-100"
            >
              {sdModels.length === 0 && <option value="">No models found</option>}
              {sdModels.map((model) => (
                <option key={model.title} value={model.title}>{model.title}</option>
              ))}
            </select>
          </div>
        </div>
      </details>
    </section>
  );
}
