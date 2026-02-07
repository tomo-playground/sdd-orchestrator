"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import type { AudioItem, MusicPreset } from "../../types";

/** Truncate string with ellipsis if too long */
const truncate = (str: string | undefined, maxLen: number) =>
  str && str.length > maxLen ? str.slice(0, maxLen - 1) + "..." : str || "";

export type BgmState = {
  bgmMode: "file" | "ai";
  bgmFile: string | null;
  bgmList: AudioItem[];
  isPreviewingBgm: boolean;
  musicPresetId: number | null;
  audioDucking: boolean;
  bgmVolume: number;
};

export type BgmActions = {
  setBgmMode: (v: "file" | "ai") => void;
  setBgmFile: (v: string | null) => void;
  onPreviewBgm: () => void;
  setMusicPresetId: (v: number | null) => void;
  setAudioDucking: (v: boolean) => void;
  setBgmVolume: (v: number) => void;
};

export type BgmSectionProps = BgmState & BgmActions;

/** BGM sub-section with File/AI mode toggle */
export default function BgmSection(props: BgmSectionProps) {
  const {
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
  } = props;
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
