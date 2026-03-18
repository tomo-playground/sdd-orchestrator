"use client";

import type { FontItem, KenBurnsPreset } from "../../types";
import VoiceStyleSection from "./VoiceStyleSection";
import BgmSection from "./BgmSection";
import InfoTooltip from "../ui/InfoTooltip";

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
  /** When true, Voice/BGM preset selection is read-only (SSOT = Stage) */
  readOnly?: boolean;
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
  readOnly = false,
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
              <div>
                <label className="mb-1 flex items-center gap-1 text-[12px] font-medium text-zinc-500">
                  Ken Burns <InfoTooltip term="ken-burns" />
                </label>
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
              </div>
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
            readOnly={readOnly}
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
            readOnly={readOnly}
          />
        </div>
      </details>
    </div>
  );
}

// Re-export RenderSidePanel for backward compatibility
export { RenderSidePanel, STAGE_LABELS } from "./RenderSidePanel";
export type { RenderSidePanelProps } from "./RenderSidePanel";

export default RenderMediaPanel;
