"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { API_BASE, ADMIN_API_BASE } from "../../constants";
import { useUIStore } from "../../store/useUIStore";
import type { MusicPreset } from "../../types";
import { TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";

/** Truncate string with ellipsis if too long */
const truncate = (str: string | undefined, maxLen: number) =>
  str && str.length > maxLen ? str.slice(0, maxLen - 1) + "..." : str || "";

export type BgmState = {
  bgmMode: "manual" | "auto";
  musicPresetId: number | null;
  isAudioDuckingEnabled: boolean;
  bgmVolume: number;
  bgmPrompt: string;
  bgmMood: string;
};

export type BgmActions = {
  setBgmMode: (v: "manual" | "auto") => void;
  setMusicPresetId: (v: number | null) => void;
  setIsAudioDuckingEnabled: (v: boolean) => void;
  setBgmVolume: (v: number) => void;
  setBgmPrompt: (v: string) => void;
};

export type BgmSectionProps = BgmState &
  BgmActions & {
    /** When true, mode/preset selection is read-only (SSOT = Stage tab) */
    readOnly?: boolean;
  };

/** BGM sub-section with Manual/Auto mode toggle */
export default function BgmSection(props: BgmSectionProps) {
  const {
    bgmMode,
    setBgmMode,
    musicPresetId,
    setMusicPresetId,
    isAudioDuckingEnabled,
    setIsAudioDuckingEnabled,
    bgmVolume,
    setBgmVolume,
    bgmPrompt,
    bgmMood,
    setBgmPrompt,
    readOnly = false,
  } = props;
  const [musicPresets, setMusicPresets] = useState<MusicPreset[]>([]);
  const [isEditingPrompt, setIsEditingPrompt] = useState(false);
  const [editPrompt, setEditPrompt] = useState("");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPreviewingAuto, setIsPreviewingAuto] = useState(false);

  useEffect(() => {
    if (bgmMode === "manual") {
      axios
        .get<MusicPreset[]>(`${API_BASE}/music-presets`)
        .then((r) => setMusicPresets(r.data))
        .catch((err) => console.warn("[BgmSection] Music presets fetch failed:", err));
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

  const previewAutoPrompt = useCallback(async () => {
    if (!bgmPrompt.trim()) return;
    setIsPreviewingAuto(true);
    try {
      const res = await axios.post<{
        audio_url: string;
        temp_asset_id: number;
        seed: number;
      }>(`${ADMIN_API_BASE}/music-presets/preview`, {
        prompt: bgmPrompt,
        duration: 10.0,
        seed: -1,
      });
      if (audioRef.current) audioRef.current.pause();
      const audio = new Audio(res.data.audio_url);
      audioRef.current = audio;
      audio.play().catch(() => {});
    } catch {
      // Preview failed silently
    } finally {
      setIsPreviewingAuto(false);
    }
  }, [bgmPrompt]);

  const hasBgm = bgmMode === "manual" ? !!musicPresetId : !!bgmPrompt;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-zinc-200 bg-zinc-50/50 p-3">
      <div className="flex items-center justify-between">
        <span className="text-[12px] font-bold tracking-wider text-zinc-500 uppercase">BGM</span>
        {readOnly ? (
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-500">
            {bgmMode === "manual" ? "Manual" : "Auto"}
          </span>
        ) : (
          <div className="flex rounded-full border border-zinc-200 bg-white p-0.5">
            {(["manual", "auto"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setBgmMode(mode)}
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold transition ${
                  bgmMode === mode ? TAB_ACTIVE : TAB_INACTIVE
                }`}
              >
                {mode === "manual" ? "Manual" : "Auto"}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {readOnly ? (
          /* ── Read-only: show current preset/prompt + link to Stage ── */
          <div className="space-y-1.5 md:col-span-2">
            {bgmMode === "manual" ? (
              <p className="text-xs text-zinc-700">
                {selectedPreset
                  ? truncate(selectedPreset.name, 28)
                  : "프리셋이 선택되지 않았습니다"}
              </p>
            ) : (
              <div className="space-y-1">
                {bgmMood && (
                  <span className="inline-flex w-fit rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-medium text-amber-700">
                    {bgmMood}
                  </span>
                )}
                <p className="text-xs text-zinc-700">{bgmPrompt || "No BGM prompt"}</p>
              </div>
            )}
            <button
              type="button"
              onClick={() => useUIStore.getState().setActiveTab("stage")}
              className="text-[11px] font-medium text-zinc-400 transition hover:text-zinc-600"
            >
              Change in Stage →
            </button>
          </div>
        ) : (
          <>
            {bgmMode === "manual" && (
              <div className="flex items-center gap-1">
                <select
                  value={musicPresetId ?? ""}
                  onChange={(e) => setMusicPresetId(e.target.value ? Number(e.target.value) : null)}
                  className="flex-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-zinc-400"
                >
                  <option value="">-- Music Preset --</option>
                  {musicPresets.map((p) => (
                    <option key={p.id} value={p.id}>
                      {truncate(p.name, 28)}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={playPresetAudio}
                  disabled={!selectedPreset?.audio_url}
                  title="Preview music preset"
                  className="rounded-full border border-zinc-200 bg-white px-2 py-2 text-[12px] text-zinc-600 disabled:text-zinc-400"
                >
                  ▶
                </button>
              </div>
            )}
            {bgmMode === "auto" && (
              <div className="flex flex-col gap-1.5 md:col-span-2">
                {bgmMood && (
                  <span className="inline-flex w-fit rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-medium text-amber-700">
                    {bgmMood}
                  </span>
                )}
                {isEditingPrompt ? (
                  <div className="flex items-center gap-1">
                    <input
                      type="text"
                      value={editPrompt}
                      onChange={(e) => setEditPrompt(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          setBgmPrompt(editPrompt);
                          setIsEditingPrompt(false);
                        } else if (e.key === "Escape") {
                          setIsEditingPrompt(false);
                        }
                      }}
                      className="flex-1 rounded-lg border border-zinc-300 bg-white px-2 py-1.5 text-xs outline-none focus:border-zinc-500"
                      placeholder="Music prompt..."
                      autoFocus
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setBgmPrompt(editPrompt);
                        setIsEditingPrompt(false);
                      }}
                      className="rounded-lg border border-zinc-200 bg-white px-2 py-1.5 text-[11px] text-zinc-600"
                    >
                      OK
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1">
                    <p
                      className="flex-1 cursor-pointer rounded-lg bg-white px-2 py-1.5 text-xs text-zinc-600"
                      onClick={() => {
                        setEditPrompt(bgmPrompt);
                        setIsEditingPrompt(true);
                      }}
                      title="Click to edit"
                    >
                      {bgmPrompt || "No BGM prompt — generate a script with Full mode to get one"}
                    </p>
                    <button
                      type="button"
                      onClick={previewAutoPrompt}
                      disabled={!bgmPrompt.trim() || isPreviewingAuto}
                      title="Preview auto BGM"
                      className="rounded-full border border-zinc-200 bg-white px-2 py-2 text-[12px] text-zinc-600 disabled:text-zinc-400"
                    >
                      {isPreviewingAuto ? "..." : "▶"}
                    </button>
                  </div>
                )}
              </div>
            )}
          </>
        )}
        {hasBgm && (
          <div className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-3 py-2">
            <span className="text-[12px] whitespace-nowrap text-zinc-500">
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
            <label className="flex items-center gap-1 text-[12px] whitespace-nowrap text-zinc-500">
              <input
                type="checkbox"
                checked={isAudioDuckingEnabled}
                onChange={(e) => setIsAudioDuckingEnabled(e.target.checked)}
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
