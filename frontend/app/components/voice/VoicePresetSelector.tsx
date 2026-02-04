"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import type { VoicePreset } from "../../types";

type Props = {
  value: number | null;
  onChange: (id: number | null) => void;
  label?: string;
  disabled?: boolean;
};

export default function VoicePresetSelector({
  value,
  onChange,
  label = "Voice Preset",
  disabled,
}: Props) {
  const [presets, setPresets] = useState<VoicePreset[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    axios
      .get<VoicePreset[]>(`${API_BASE}/voice-presets`)
      .then((r) => setPresets(r.data))
      .catch(() => {});
  }, []);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const selectedPreset = presets.find((p) => p.id === value);

  const handlePreview = () => {
    if (!selectedPreset?.audio_url) return;

    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setIsPlaying(false);
      return;
    }

    const audio = new Audio(selectedPreset.audio_url);
    audioRef.current = audio;
    setIsPlaying(true);
    audio.play().catch(() => {});
    audio.onended = () => {
      setIsPlaying(false);
      audioRef.current = null;
    };
  };

  return (
    <div>
      <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <select
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
          disabled={disabled}
          className="flex-1 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 outline-none focus:border-zinc-400 disabled:opacity-50"
        >
          <option value="">-- None --</option>
          {presets.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
              {p.description ? ` \u2014 ${p.description}` : ""}
            </option>
          ))}
        </select>
        {selectedPreset?.audio_url && (
          <button
            type="button"
            onClick={handlePreview}
            className="shrink-0 rounded-lg border border-zinc-200 bg-white px-2.5 py-2 text-xs text-zinc-600 transition hover:bg-zinc-50"
            title={isPlaying ? "Stop" : "Preview"}
          >
            {isPlaying ? "\u25A0" : "\u25B6"}
          </button>
        )}
      </div>
    </div>
  );
}
