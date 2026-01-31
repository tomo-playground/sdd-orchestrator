"use client";

import type { AudioItem, FontItem, KenBurnsPreset, OverlaySettings, PostCardSettings } from "../../types";
import { VOICES } from "../../constants";

// Ken Burns preset options for dropdown
const KEN_BURNS_OPTIONS: { value: KenBurnsPreset; label: string }[] = [
  { value: "none", label: "None" },
  { value: "zoom_in_center", label: "Zoom In (Center)" },
  { value: "zoom_out_center", label: "Zoom Out (Center)" },
  { value: "pan_left", label: "Pan Left → Right" },
  { value: "pan_right", label: "Pan Right → Left" },
  { value: "pan_up", label: "Pan Up" },
  { value: "pan_down", label: "Pan Down" },
  { value: "zoom_pan_left", label: "Zoom + Pan Left" },
  { value: "zoom_pan_right", label: "Zoom + Pan Right" },
  { value: "pan_up_vertical", label: "Pan Up (Vertical) ⬆️" },
  { value: "pan_down_vertical", label: "Pan Down (Vertical) ⬇️" },
  { value: "zoom_in_bottom", label: "Zoom In (Bottom) 🔍" },
  { value: "zoom_in_top", label: "Zoom In (Top) 🔍" },
  { value: "pan_zoom_up", label: "Pan + Zoom Up ⬆️🔍" },
  { value: "pan_zoom_down", label: "Pan + Zoom Down ⬇️🔍" },
  { value: "random", label: "Random (per scene)" },
];

// Transition preset options for dropdown
const TRANSITION_OPTIONS: { value: string; label: string; visual: string }[] = [
  { value: "fade", label: "Fade", visual: "○→●" },
  { value: "wipeleft", label: "Wipe Left", visual: "▐←" },
  { value: "wiperight", label: "Wipe Right", visual: "→▌" },
  { value: "slideup", label: "Slide Up", visual: "[↑]" },
  { value: "slidedown", label: "Slide Down", visual: "[↓]" },
  { value: "circleopen", label: "Circle Open", visual: "◉→" },
  { value: "dissolve", label: "Dissolve", visual: "▓▒░" },
  { value: "random", label: "Random (per scene)", visual: "🎲" },
];

/** Truncate string with ellipsis if too long */
const truncate = (str: string | undefined, maxLen: number) =>
  str && str.length > maxLen ? str.slice(0, maxLen - 1) + "…" : (str || "");

type RenderSettingsPanelProps = {
  // Layout
  layoutStyle: "full" | "post";
  setLayoutStyle: (value: "full" | "post") => void;
  frameStyle: string;
  setFrameStyle: (value: string) => void;
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
  kenBurnsPreset: KenBurnsPreset;
  setKenBurnsPreset: (value: KenBurnsPreset) => void;
  kenBurnsIntensity: number;
  setKenBurnsIntensity: (value: number) => void;
  transitionType: string;
  setTransitionType: (value: string) => void;
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
  // Current Style
  currentStyleProfile: {
    id: number;
    name: string;
    display_name: string | null;
    sd_model_name: string | null;
    loras: { name: string; trigger_words: string[]; weight: number }[];
    negative_embeddings: { name: string; trigger_word: string }[];
    positive_embeddings: { name: string; trigger_word: string }[];
    default_positive: string | null;
    default_negative: string | null;
  } | null;
};

export default function RenderSettingsPanel({
  layoutStyle,
  setLayoutStyle,
  frameStyle,
  setFrameStyle,
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
  kenBurnsPreset,
  setKenBurnsPreset,
  kenBurnsIntensity,
  setKenBurnsIntensity,
  transitionType,
  setTransitionType,
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
  currentStyleProfile,
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
        <div className="flex items-center gap-3">
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
          {layoutStyle === "full" && (
            <>
              <span className="text-zinc-300">|</span>
              <select
                value={frameStyle}
                onChange={(e) => setFrameStyle(e.target.value)}
                className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
              >
                <option value="overlay_minimal.png">Minimal</option>
                <option value="overlay_modern.png">Modern</option>
                <option value="overlay_classic.png">Classic</option>
              </select>
            </>
          )}
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
          <div className="grid gap-3 md:grid-cols-3">
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
              {fontList.map((font, idx) => (
                <option key={`${font.name}-${idx}`} value={font.name}>{truncate(font.name, 20)}</option>
              ))}
            </select>
            <div
              className="rounded-xl border border-zinc-200 bg-zinc-900 px-3 py-2 text-center text-white text-sm"
              style={{
                fontFamily: loadedFonts.has(subtitleFont)
                  ? `"${subtitleFont}", sans-serif`
                  : "sans-serif",
              }}
            >
              {loadedFonts.has(subtitleFont) ? "가나다 ABC" : "Loading..."}
            </div>
          </div>
          {/* Motion Effects Row */}
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-3">
              <select
                value={kenBurnsPreset}
                onChange={(e) => setKenBurnsPreset(e.target.value as KenBurnsPreset)}
                title="Ken Burns Effect (Image Motion)"
                className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
              >
                {KEN_BURNS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              {kenBurnsPreset !== "none" && (
                <div className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-white px-3 py-2">
                  <span className="text-xs text-zinc-500 whitespace-nowrap">Intensity</span>
                  <span className="text-[10px] text-zinc-400">{kenBurnsIntensity.toFixed(1)}x</span>
                  <input
                    type="range"
                    min={0.5}
                    max={2.0}
                    step={0.1}
                    value={kenBurnsIntensity}
                    onChange={(e) => setKenBurnsIntensity(Number(e.target.value))}
                    className="flex-1 accent-zinc-900"
                  />
                </div>
              )}
            </div>
            <select
              value={transitionType}
              onChange={(e) => setTransitionType(e.target.value)}
              title="Scene Transition"
              className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
            >
              {TRANSITION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.visual} {opt.label}
                </option>
              ))}
            </select>
          </div>
          {/* Audio Row */}
          <div className="grid gap-3 md:grid-cols-2">
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
              <span className="text-[10px] text-zinc-500 whitespace-nowrap">Speed {speedMultiplier.toFixed(2)}x</span>
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
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="flex items-center gap-1">
              <select
                value={bgmFile ?? ""}
                onChange={(e) => setBgmFile(e.target.value || null)}
                title="BGM"
                className="flex-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
              >
                <option value="">BGM: None</option>
                <option value="random">Random</option>
                {bgmList.map((bgm) => (
                  <option key={bgm.name} value={bgm.name}>{truncate(bgm.name, 28)}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => onPreviewBgm()}
                disabled={!bgmFile || bgmFile === "random" || isPreviewingBgm}
                title={bgmFile === "random" ? "Cannot preview random" : "Preview BGM"}
                className="rounded-full border border-zinc-200 bg-white px-2 py-2 text-[10px] text-zinc-600 disabled:text-zinc-400"
              >
                ▶
              </button>
            </div>
            {bgmFile && (
              <div className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-3 py-2">
                <span className="text-[10px] text-zinc-500 whitespace-nowrap">{Math.round(bgmVolume * 100)}%</span>
                <input
                  type="range"
                  min={0.05}
                  max={0.5}
                  step={0.05}
                  value={bgmVolume}
                  onChange={(e) => setBgmVolume(Number(e.target.value))}
                  className="flex-1 accent-zinc-900"
                />
                <label className="flex items-center gap-1 text-[10px] text-zinc-500 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={audioDucking}
                    onChange={(e) => setAudioDucking(e.target.checked)}
                    className="h-3 w-3 accent-zinc-900"
                  />
                  Duck
                </label>
              </div>
            )}
          </div>
        </div>
      </details>

      {/* 3. CURRENT STYLE (Read-only) */}
      <div className="rounded-2xl border border-zinc-200 bg-gradient-to-br from-indigo-50/50 to-white p-5">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
            Current Style
          </h3>
          <a
            href="/manage?tab=style"
            className="rounded-full bg-white border border-zinc-200 px-3 py-1.5 text-[10px] font-semibold text-zinc-600 hover:bg-zinc-50 transition"
          >
            Change
          </a>
        </div>

        {currentStyleProfile ? (
          <div className="grid gap-3">
            <div>
              <span className="text-[10px] font-semibold text-zinc-500 uppercase block mb-1">Profile</span>
              <p className="text-sm font-bold text-zinc-900">
                {currentStyleProfile.display_name || currentStyleProfile.name}
              </p>
            </div>
            {currentStyleProfile.sd_model_name && (
              <div>
                <span className="text-[10px] font-semibold text-zinc-500 uppercase block mb-1">SD Model</span>
                <p className="text-xs text-zinc-700">
                  {currentStyleProfile.sd_model_name}
                </p>
              </div>
            )}
            {currentStyleProfile.loras && currentStyleProfile.loras.length > 0 && (
              <div>
                <span className="text-[10px] font-semibold text-zinc-500 uppercase block mb-1">LoRAs</span>
                <div className="flex flex-wrap gap-1">
                  {currentStyleProfile.loras.map((lora) => (
                    <span key={lora.name} className="rounded-full bg-blue-100 px-2 py-0.5 text-[9px] text-blue-700 font-medium">
                      {lora.name.split('.')[0]} ({lora.weight})
                    </span>
                  ))}
                </div>
              </div>
            )}
            {((currentStyleProfile.negative_embeddings && currentStyleProfile.negative_embeddings.length > 0) ||
              (currentStyleProfile.positive_embeddings && currentStyleProfile.positive_embeddings.length > 0)) && (
              <div>
                <span className="text-[10px] font-semibold text-zinc-500 uppercase block mb-1">Embeddings</span>
                <div className="flex flex-wrap gap-1">
                  {currentStyleProfile.positive_embeddings?.map((emb, idx) => (
                    <span key={emb.name || `pos-${idx}`} className="rounded-full bg-emerald-100 px-2 py-0.5 text-[9px] text-emerald-700 font-medium">
                      {emb.name}
                    </span>
                  ))}
                  {currentStyleProfile.negative_embeddings?.map((emb, idx) => (
                    <span key={emb.name || `neg-${idx}`} className="rounded-full bg-rose-100 px-2 py-0.5 text-[9px] text-rose-700 font-medium">
                      {emb.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-zinc-300 bg-white/50 p-4 text-center">
            <p className="text-xs text-zinc-400 mb-2">No style profile selected</p>
            <a
              href="/manage?tab=style"
              className="inline-block rounded-full bg-indigo-500 px-4 py-1.5 text-[10px] font-semibold text-white hover:bg-indigo-600 transition"
            >
              Select Profile
            </a>
          </div>
        )}
      </div>
    </section>
  );
}
