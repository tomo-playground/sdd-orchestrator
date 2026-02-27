"use client";

import type { FontItem, KenBurnsPreset, RenderProgress, RenderStage } from "../../types";
import { SIDE_PANEL_LABEL, TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";
import VoiceStyleSection from "./VoiceStyleSection";
import BgmSection from "./BgmSection";

// Ken Burns preset options for dropdown
const KEN_BURNS_OPTIONS: { value: KenBurnsPreset; label: string }[] = [
  { value: "none", label: "None" },
  { value: "zoom_in_center", label: "Zoom In (Center)" },
  { value: "zoom_out_center", label: "Zoom Out (Center)" },
  { value: "pan_left", label: "Pan Left \u2192 Right" },
  { value: "pan_right", label: "Pan Right \u2192 Left" },
  { value: "pan_up", label: "Pan Up" },
  { value: "pan_down", label: "Pan Down" },
  { value: "zoom_pan_left", label: "Zoom + Pan Left" },
  { value: "zoom_pan_right", label: "Zoom + Pan Right" },
  { value: "pan_up_vertical", label: "Pan Up (Vertical)" },
  { value: "pan_down_vertical", label: "Pan Down (Vertical)" },
  { value: "zoom_in_bottom", label: "Zoom In (Bottom)" },
  { value: "zoom_in_top", label: "Zoom In (Top)" },
  { value: "pan_zoom_up", label: "Pan + Zoom Up" },
  { value: "pan_zoom_down", label: "Pan + Zoom Down" },
  { value: "random", label: "Random (per scene)" },
];

// Transition preset options for dropdown
const TRANSITION_OPTIONS: { value: string; label: string; visual: string }[] = [
  { value: "fade", label: "Fade", visual: "\u25CB\u2192\u25CF" },
  { value: "wipeleft", label: "Wipe Left", visual: "\u2590\u2190" },
  { value: "wiperight", label: "Wipe Right", visual: "\u2192\u258C" },
  { value: "slideup", label: "Slide Up", visual: "[\u2191]" },
  { value: "slidedown", label: "Slide Down", visual: "[\u2193]" },
  { value: "circleopen", label: "Circle Open", visual: "\u25C9\u2192" },
  { value: "dissolve", label: "Dissolve", visual: "\u2593\u2592\u2591" },
  { value: "random", label: "Random (per scene)", visual: "\uD83C\uDFB2" },
];

/** Truncate string with ellipsis if too long */
const truncate = (str: string | undefined, maxLen: number) =>
  str && str.length > maxLen ? str.slice(0, maxLen - 1) + "\u2026" : str || "";

/* ======== Media Settings Panel (left column) ======== */

export type RenderMediaPanelProps = {
  includeSceneText: boolean;
  setIncludeSceneText: (value: boolean) => void;
  sceneTextFont: string;
  setSceneTextFont: (value: string) => void;
  fontList: FontItem[];
  loadedFonts: Set<string>;
  kenBurnsPreset: KenBurnsPreset;
  setKenBurnsPreset: (value: KenBurnsPreset) => void;
  kenBurnsIntensity: number;
  setKenBurnsIntensity: (value: number) => void;
  transitionType: string;
  setTransitionType: (value: string) => void;
  speedMultiplier: number;
  setSpeedMultiplier: (value: number) => void;
  audioDucking: boolean;
  setAudioDucking: (value: boolean) => void;
  bgmVolume: number;
  setBgmVolume: (value: number) => void;
  voiceDesignPrompt: string;
  setVoiceDesignPrompt: (value: string) => void;
  voicePresetId?: number | null;
  setVoicePresetId?: (value: number | null) => void;
  bgmMode: "manual" | "auto";
  setBgmMode: (value: "manual" | "auto") => void;
  musicPresetId: number | null;
  setMusicPresetId: (value: number | null) => void;
  bgmPrompt: string;
  bgmMood: string;
  setBgmPrompt: (value: string) => void;
  defaultOpen?: boolean;
};

export function RenderMediaPanel({
  includeSceneText,
  setIncludeSceneText,
  sceneTextFont,
  setSceneTextFont,
  fontList,
  loadedFonts,
  kenBurnsPreset,
  setKenBurnsPreset,
  kenBurnsIntensity,
  setKenBurnsIntensity,
  transitionType,
  setTransitionType,
  speedMultiplier,
  setSpeedMultiplier,
  audioDucking,
  setAudioDucking,
  bgmVolume,
  setBgmVolume,
  voiceDesignPrompt,
  setVoiceDesignPrompt,
  voicePresetId,
  setVoicePresetId,
  bgmMode,
  setBgmMode,
  musicPresetId,
  setMusicPresetId,
  bgmPrompt,
  bgmMood,
  setBgmPrompt,
  defaultOpen = true,
}: RenderMediaPanelProps) {
  const accordionSummary =
    "flex cursor-pointer items-center justify-between px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase";
  const accordionChevron = "text-zinc-400 transition group-open:rotate-180";
  const accordionWrapper = "group rounded-2xl border border-zinc-200 bg-white";

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-zinc-900">Render</h2>
        <p className="text-xs text-zinc-500">Layout, audio, and output settings.</p>
      </div>

      {/* ── Media ── */}
      <details open={defaultOpen || undefined} className={accordionWrapper}>
        <summary className={accordionSummary}>
          Media
          <span className={accordionChevron}>{"\u25BC"}</span>
        </summary>
        <div className="grid gap-4 border-t border-zinc-100 p-4">
          <div className="grid gap-3 md:grid-cols-3">
            <label className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs font-medium text-zinc-600">
              Scene Text
              <input
                type="checkbox"
                checked={includeSceneText}
                onChange={(e) => setIncludeSceneText(e.target.checked)}
                className="h-4 w-4 accent-zinc-900"
              />
            </label>
            <select
              value={sceneTextFont ?? ""}
              onChange={(e) => setSceneTextFont(e.target.value)}
              title="Scene Text Font"
              className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
            >
              {fontList.length === 0 && <option value="">Default</option>}
              {fontList.map((font, idx) => (
                <option key={`${font.name}-${idx}`} value={font.name}>
                  {truncate(font.name, 20)}
                </option>
              ))}
            </select>
            <div
              className="rounded-xl border border-zinc-200 bg-zinc-900 px-3 py-2 text-center text-sm text-white"
              style={{
                fontFamily: loadedFonts.has(sceneTextFont)
                  ? `"${sceneTextFont}", sans-serif`
                  : "sans-serif",
              }}
            >
              {loadedFonts.has(sceneTextFont) ? "\uAC00\uB098\uB2E4 ABC" : "Loading..."}
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-3">
              <select
                value={kenBurnsPreset}
                onChange={(e) => setKenBurnsPreset(e.target.value as KenBurnsPreset)}
                title="Ken Burns Effect (Image Motion)"
                className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
              >
                {KEN_BURNS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              {kenBurnsPreset !== "none" && (
                <div className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-white px-3 py-2">
                  <span className="text-xs whitespace-nowrap text-zinc-500">Intensity</span>
                  <span className="text-[12px] text-zinc-400">{kenBurnsIntensity.toFixed(1)}x</span>
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
        </div>
      </details>

      {/* ── Voice ── */}
      <details open={defaultOpen || undefined} className={accordionWrapper}>
        <summary className={accordionSummary}>
          Voice
          <span className={accordionChevron}>{"\u25BC"}</span>
        </summary>
        <div className="border-t border-zinc-100 p-4">
          <VoiceStyleSection
            voicePresetId={voicePresetId}
            setVoicePresetId={setVoicePresetId}
            voiceDesignPrompt={voiceDesignPrompt}
            setVoiceDesignPrompt={setVoiceDesignPrompt}
            speedMultiplier={speedMultiplier}
            setSpeedMultiplier={setSpeedMultiplier}
          />
        </div>
      </details>

      {/* ── BGM ── */}
      <details open={defaultOpen || undefined} className={accordionWrapper}>
        <summary className={accordionSummary}>
          BGM
          <span className={accordionChevron}>{"\u25BC"}</span>
        </summary>
        <div className="border-t border-zinc-100 p-4">
          <BgmSection
            bgmMode={bgmMode}
            setBgmMode={setBgmMode}
            musicPresetId={musicPresetId}
            setMusicPresetId={setMusicPresetId}
            audioDucking={audioDucking}
            setAudioDucking={setAudioDucking}
            bgmVolume={bgmVolume}
            setBgmVolume={setBgmVolume}
            bgmPrompt={bgmPrompt}
            bgmMood={bgmMood}
            setBgmPrompt={setBgmPrompt}
          />
        </div>
      </details>
    </div>
  );
}

/* ======== Render Side Panel (right column) ======== */

export const STAGE_LABELS: Record<RenderStage, string> = {
  queued: "\uB300\uAE30\uC911",
  setup_avatars: "\uC544\uBC14\uD0C0 \uC124\uC815",
  process_scenes: "\uC74C\uC131 \uC0DD\uC131",
  calculate_durations: "\uC2DC\uAC04 \uACC4\uC0B0",
  prepare_bgm: "BGM \uC900\uBE44",
  build_filters: "\uD544\uD130 \uAD6C\uC131",
  encode: "\uC778\uCF54\uB529",
  upload: "\uC5C5\uB85C\uB4DC",
  completed: "\uC644\uB8CC",
  failed: "\uC2E4\uD328",
};

export type RenderSidePanelProps = {
  layoutStyle: "full" | "post";
  setLayoutStyle: (value: "full" | "post") => void;
  frameStyle: string;
  setFrameStyle: (value: string) => void;
  canRender: boolean;
  isRendering: boolean;
  scenesWithImages: number;
  totalScenes: number;
  onRender: () => void;
  disabledReason?: string | null;
  renderPresetName?: string | null;
  renderPresetSource?: string | null;
  renderProgress?: RenderProgress | null;
};

export function RenderSidePanel({
  layoutStyle,
  setLayoutStyle,
  frameStyle,
  setFrameStyle,
  canRender,
  isRendering,
  scenesWithImages,
  totalScenes,
  onRender,
  disabledReason,
  renderPresetName,
  renderPresetSource,
  renderProgress,
}: RenderSidePanelProps) {
  return (
    <>
      {/* Layout */}
      <div>
        <label className={SIDE_PANEL_LABEL}>Layout</label>
        <div className="flex rounded-full border border-zinc-200 bg-zinc-50 p-0.5">
          <button
            type="button"
            onClick={() => setLayoutStyle("full")}
            className={`flex-1 rounded-full px-3 py-1.5 text-[12px] font-semibold transition ${
              layoutStyle === "full" ? TAB_ACTIVE : TAB_INACTIVE
            }`}
          >
            Full 9:16
          </button>
          <button
            type="button"
            onClick={() => setLayoutStyle("post")}
            className={`flex-1 rounded-full px-3 py-1.5 text-[12px] font-semibold transition ${
              layoutStyle === "post" ? TAB_ACTIVE : TAB_INACTIVE
            }`}
          >
            Post 1:1
          </button>
        </div>
        {layoutStyle === "full" && (
          <select
            value={frameStyle}
            onChange={(e) => setFrameStyle(e.target.value)}
            className="mt-2 w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-[12px] outline-none focus:border-zinc-400"
          >
            <option value="overlay_minimal.png">Minimal</option>
            <option value="overlay_modern.png">Modern</option>
            <option value="overlay_classic.png">Classic</option>
          </select>
        )}
      </div>

      {/* Render Action */}
      <div className="flex flex-col items-center gap-2">
        <button
          onClick={onRender}
          disabled={!canRender || isRendering}
          title={disabledReason || undefined}
          className="w-full rounded-full bg-zinc-900 py-2.5 text-xs font-semibold text-white shadow-lg transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isRendering ? "Rendering..." : "Render"}
        </button>

        {/* Progress Bar */}
        {isRendering && renderProgress && (
          <div className="w-full space-y-1.5">
            <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-200">
              <div
                className="h-full rounded-full bg-zinc-900 transition-all duration-300 ease-out"
                style={{ width: `${renderProgress.percent}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[12px] text-zinc-500">
              <span>
                {STAGE_LABELS[renderProgress.stage] || renderProgress.stage}
                {renderProgress.message ? ` (${renderProgress.message})` : ""}
              </span>
              <span className="font-medium">{renderProgress.percent}%</span>
            </div>
            {renderProgress.estimated_remaining_seconds != null &&
              renderProgress.estimated_remaining_seconds > 0 && (
                <p className="text-[11px] text-zinc-400">
                  남은 시간: ~{Math.ceil(renderProgress.estimated_remaining_seconds)}초
                </p>
              )}
          </div>
        )}

        <span className="text-[12px] text-zinc-400">
          Images: {scenesWithImages}/{totalScenes}
        </span>
        {disabledReason && (
          <p className="rounded-full bg-amber-50 px-2.5 py-1 text-center text-[12px] font-medium text-amber-600">
            {disabledReason}
          </p>
        )}
      </div>

      {/* Preset */}
      {renderPresetName && (
        <div>
          <label className={SIDE_PANEL_LABEL}>Preset</label>
          <p className="text-xs font-medium text-indigo-600">{renderPresetName}</p>
          {renderPresetSource && (
            <p className="text-[11px] text-indigo-400">from {renderPresetSource}</p>
          )}
        </div>
      )}
    </>
  );
}

export default RenderMediaPanel;
