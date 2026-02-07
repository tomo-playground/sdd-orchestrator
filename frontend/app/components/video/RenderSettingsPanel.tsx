"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import type {
  AudioItem,
  FontItem,
  KenBurnsPreset,
  MusicPreset,
  RenderProgress,
  RenderStage,
  VoicePreset,
} from "../../types";
import { SIDE_PANEL_CLASSES, SIDE_PANEL_LABEL } from "../ui/variants";

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
  str && str.length > maxLen ? str.slice(0, maxLen - 1) + "…" : str || "";

/** Voice Style sub-section with preset selector */
function VoiceStyleSection({
  voicePresetId,
  setVoicePresetId,
  voiceDesignPrompt,
  setVoiceDesignPrompt,
  speedMultiplier,
  setSpeedMultiplier,
}: {
  voicePresetId?: number | null;
  setVoicePresetId?: (v: number | null) => void;
  voiceDesignPrompt: string;
  setVoiceDesignPrompt: (v: string) => void;
  speedMultiplier: number;
  setSpeedMultiplier: (v: number) => void;
}) {
  const [voicePresets, setVoicePresets] = useState<VoicePreset[]>([]);

  useEffect(() => {
    axios
      .get<VoicePreset[]>(`${API_BASE}/voice-presets`)
      .then((r) => setVoicePresets(r.data))
      .catch(() => {});
  }, []);

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-zinc-200 bg-zinc-50/50 p-3">
      <span className="text-[10px] font-bold tracking-wider text-zinc-500 uppercase">Voice</span>
      <div className="grid gap-2">
        {setVoicePresetId && (
          <select
            value={voicePresetId ?? ""}
            onChange={(e) => setVoicePresetId(e.target.value ? Number(e.target.value) : null)}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
          >
            <option value="">-- Voice Preset (auto) --</option>
            {voicePresets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        )}

        {!voicePresetId && (
          <div className="space-y-2">
            <input
              type="text"
              value={voiceDesignPrompt}
              onChange={(e) => setVoiceDesignPrompt(e.target.value)}
              placeholder="Voice style (e.g. calm 40s female)"
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
            />
            <p className="text-[9px] text-zinc-400">
              프리셋 미선택 시, 스타일 텍스트로 음성을 생성합니다.
            </p>
          </div>
        )}

        {voicePresetId && (
          <p className="text-[9px] text-indigo-500">
            Voice preset selected — all scenes will use the same cloned voice.
          </p>
        )}

        <div className="flex items-center gap-2">
          <span className="text-[9px] whitespace-nowrap text-zinc-500">
            Speed x{speedMultiplier.toFixed(2)}
          </span>
          <input
            type="range"
            min={0.8}
            max={1.5}
            step={0.05}
            value={speedMultiplier}
            onChange={(e) => setSpeedMultiplier(Number(e.target.value))}
            className="h-1.5 flex-1 accent-zinc-900"
          />
        </div>
      </div>
    </div>
  );
}

/** BGM sub-section with File/AI mode toggle */
function BgmSection({
  bgmMode,
  setBgmMode,
  bgmFile,
  setBgmFile,
  bgmList,
  onPreviewBgm,
  isPreviewingBgm,
  musicPresetId,
  setMusicPresetId,
  audioDucking,
  setAudioDucking,
  bgmVolume,
  setBgmVolume,
}: {
  bgmMode: "file" | "ai";
  setBgmMode: (v: "file" | "ai") => void;
  bgmFile: string | null;
  setBgmFile: (v: string | null) => void;
  bgmList: AudioItem[];
  onPreviewBgm: () => void;
  isPreviewingBgm: boolean;
  musicPresetId: number | null;
  setMusicPresetId: (v: number | null) => void;
  audioDucking: boolean;
  setAudioDucking: (v: boolean) => void;
  bgmVolume: number;
  setBgmVolume: (v: number) => void;
}) {
  const [musicPresets, setMusicPresets] = useState<MusicPreset[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (bgmMode === "ai") {
      axios
        .get<MusicPreset[]>(`${API_BASE}/music-presets`)
        .then((r) => setMusicPresets(r.data))
        .catch(() => {});
    }
  }, [bgmMode]);

  const selectedPreset = musicPresets.find((p) => p.id === musicPresetId);

  const playPresetAudio = useCallback(() => {
    if (!selectedPreset?.audio_url) return;
    if (audioRef.current) audioRef.current.pause();
    const audio = new Audio(selectedPreset.audio_url);
    audioRef.current = audio;
    audio.play().catch(() => {});
  }, [selectedPreset]);

  const hasBgm = bgmMode === "ai" ? !!musicPresetId : !!bgmFile;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-zinc-200 bg-zinc-50/50 p-3">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold tracking-wider text-zinc-500 uppercase">BGM</span>
        <div className="flex rounded-full border border-zinc-200 bg-white p-0.5">
          <button
            type="button"
            onClick={() => setBgmMode("file")}
            className={`rounded-full px-2.5 py-0.5 text-[9px] font-semibold transition ${
              bgmMode === "file" ? "bg-zinc-900 text-white" : "text-zinc-500 hover:text-zinc-700"
            }`}
          >
            File
          </button>
          <button
            type="button"
            onClick={() => setBgmMode("ai")}
            className={`rounded-full px-2.5 py-0.5 text-[9px] font-semibold transition ${
              bgmMode === "ai" ? "bg-zinc-900 text-white" : "text-zinc-500 hover:text-zinc-700"
            }`}
          >
            AI
          </button>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {bgmMode === "file" ? (
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
                <option key={bgm.name} value={bgm.name}>
                  {truncate(bgm.name, 28)}
                </option>
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
        ) : (
          <div className="flex items-center gap-1">
            <select
              value={musicPresetId ?? ""}
              onChange={(e) => setMusicPresetId(e.target.value ? Number(e.target.value) : null)}
              className="flex-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
            >
              <option value="">-- Music Preset --</option>
              {musicPresets.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={playPresetAudio}
              disabled={!selectedPreset?.audio_url}
              title="Preview music preset"
              className="rounded-full border border-zinc-200 bg-white px-2 py-2 text-[10px] text-zinc-600 disabled:text-zinc-400"
            >
              ▶
            </button>
          </div>
        )}
        {hasBgm && (
          <div className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-3 py-2">
            <span className="text-[10px] whitespace-nowrap text-zinc-500">
              {Math.round(bgmVolume * 100)}%
            </span>
            <input
              type="range"
              min={0.05}
              max={0.5}
              step={0.05}
              value={bgmVolume}
              onChange={(e) => setBgmVolume(Number(e.target.value))}
              className="flex-1 accent-zinc-900"
            />
            <label className="flex items-center gap-1 text-[10px] whitespace-nowrap text-zinc-500">
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
  );
}

/* ======== Media Settings Panel (left column) ======== */

export type RenderMediaPanelProps = {
  includeSceneText: boolean;
  setIncludeSceneText: (value: boolean) => void;
  sceneTextFont: string;
  setSubtitleFont: (value: string) => void;
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
  bgmFile: string | null;
  setBgmFile: (value: string | null) => void;
  bgmList: AudioItem[];
  onPreviewBgm: () => void;
  isPreviewingBgm: boolean;
  audioDucking: boolean;
  setAudioDucking: (value: boolean) => void;
  bgmVolume: number;
  setBgmVolume: (value: number) => void;
  voiceDesignPrompt: string;
  setVoiceDesignPrompt: (value: string) => void;
  voicePresetId?: number | null;
  setVoicePresetId?: (value: number | null) => void;
  bgmMode: "file" | "ai";
  setBgmMode: (value: "file" | "ai") => void;
  musicPresetId: number | null;
  setMusicPresetId: (value: number | null) => void;
};

export function RenderMediaPanel({
  includeSceneText,
  setIncludeSceneText,
  sceneTextFont,
  setSubtitleFont,
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
  bgmFile,
  setBgmFile,
  bgmList,
  onPreviewBgm,
  isPreviewingBgm,
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
}: RenderMediaPanelProps) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-zinc-900">Render</h2>
        <p className="text-xs text-zinc-500">Layout, audio, and output settings.</p>
      </div>

      <details open className="group rounded-2xl border border-zinc-200 bg-white">
        <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
          Media
          <span className="text-zinc-400 transition group-open:rotate-180">▼</span>
        </summary>
        <div className="grid gap-4 border-t border-zinc-100 p-4">
          {/* Video Row */}
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
              onChange={(e) => setSubtitleFont(e.target.value)}
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
              {loadedFonts.has(sceneTextFont) ? "가나다 ABC" : "Loading..."}
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
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              {kenBurnsPreset !== "none" && (
                <div className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-white px-3 py-2">
                  <span className="text-xs whitespace-nowrap text-zinc-500">Intensity</span>
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
          {/* Voice */}
          <VoiceStyleSection
            voicePresetId={voicePresetId}
            setVoicePresetId={setVoicePresetId}
            voiceDesignPrompt={voiceDesignPrompt}
            setVoiceDesignPrompt={setVoiceDesignPrompt}
            speedMultiplier={speedMultiplier}
            setSpeedMultiplier={setSpeedMultiplier}
          />
          {/* BGM */}
          <BgmSection
            bgmMode={bgmMode}
            setBgmMode={setBgmMode}
            bgmFile={bgmFile}
            setBgmFile={setBgmFile}
            bgmList={bgmList}
            onPreviewBgm={onPreviewBgm}
            isPreviewingBgm={isPreviewingBgm}
            musicPresetId={musicPresetId}
            setMusicPresetId={setMusicPresetId}
            audioDucking={audioDucking}
            setAudioDucking={setAudioDucking}
            bgmVolume={bgmVolume}
            setBgmVolume={setBgmVolume}
          />
        </div>
      </details>
    </div>
  );
}

/* ======== Render Side Panel (right column) ======== */

const STAGE_LABELS: Record<RenderStage, string> = {
  queued: "대기중",
  setup_avatars: "아바타 설정",
  process_scenes: "음성 생성",
  calculate_durations: "시간 계산",
  prepare_bgm: "BGM 준비",
  build_filters: "필터 구성",
  encode: "인코딩",
  upload: "업로드",
  completed: "완료",
  failed: "실패",
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
    <div className={SIDE_PANEL_CLASSES}>
      {/* Layout */}
      <div>
        <label className={SIDE_PANEL_LABEL}>Layout</label>
        <div className="flex rounded-full border border-zinc-200 bg-zinc-50 p-0.5">
          <button
            type="button"
            onClick={() => setLayoutStyle("full")}
            className={`flex-1 rounded-full px-3 py-1.5 text-[10px] font-semibold transition ${
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
            className={`flex-1 rounded-full px-3 py-1.5 text-[10px] font-semibold transition ${
              layoutStyle === "post"
                ? "bg-zinc-900 text-white"
                : "text-zinc-500 hover:text-zinc-700"
            }`}
          >
            Post 1:1
          </button>
        </div>
        {layoutStyle === "full" && (
          <select
            value={frameStyle}
            onChange={(e) => setFrameStyle(e.target.value)}
            className="mt-2 w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-[10px] outline-none focus:border-zinc-400"
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
            <div className="flex items-center justify-between text-[10px] text-zinc-500">
              <span>
                {STAGE_LABELS[renderProgress.stage] || renderProgress.stage}
                {renderProgress.stage_detail ? ` (${renderProgress.stage_detail})` : ""}
              </span>
              <span className="font-medium">{renderProgress.percent}%</span>
            </div>
          </div>
        )}

        <span className="text-[10px] text-zinc-400">
          Images: {scenesWithImages}/{totalScenes}
        </span>
        {disabledReason && (
          <p className="rounded-full bg-amber-50 px-2.5 py-1 text-center text-[10px] font-medium text-amber-600">
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
            <p className="text-[9px] text-indigo-400">from {renderPresetSource}</p>
          )}
        </div>
      )}
    </div>
  );
}

/* ======== Legacy default export (kept for backwards compat if needed) ======== */
export default RenderMediaPanel;
