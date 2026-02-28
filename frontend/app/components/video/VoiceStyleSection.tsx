"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import { useUIStore } from "../../store/useUIStore";
import type { VoicePreset } from "../../types";

export type VoiceStyleSectionProps = {
  voicePresetId?: number | null;
  setVoicePresetId?: (v: number | null) => void;
  voiceDesignPrompt: string;
  setVoiceDesignPrompt: (v: string) => void;
  speedMultiplier: number;
  setSpeedMultiplier: (v: number) => void;
  /** When true, preset selection is read-only (SSOT = Stage tab) */
  readOnly?: boolean;
};

/** Voice Style sub-section with preset selector */
export default function VoiceStyleSection({
  voicePresetId,
  setVoicePresetId,
  voiceDesignPrompt,
  setVoiceDesignPrompt,
  speedMultiplier,
  setSpeedMultiplier,
  readOnly = false,
}: VoiceStyleSectionProps) {
  const [voicePresets, setVoicePresets] = useState<VoicePreset[]>([]);

  useEffect(() => {
    axios
      .get<VoicePreset[]>(`${API_BASE}/voice-presets`)
      .then((r) => setVoicePresets(r.data))
      .catch(() => {});
  }, []);

  const selectedPresetName = voicePresets.find((p) => p.id === voicePresetId)?.name ?? null;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-zinc-200 bg-zinc-50/50 p-3">
      <span className="text-[12px] font-bold tracking-wider text-zinc-500 uppercase">Voice</span>
      <div className="grid gap-2">
        {readOnly ? (
          /* ── Read-only: show current preset/design text + link to Stage ── */
          <div className="space-y-1.5">
            <p className="text-xs text-zinc-700">
              {selectedPresetName ? selectedPresetName : voiceDesignPrompt || "Auto (no preset)"}
            </p>
            {voicePresetId && (
              <p className="text-[11px] text-indigo-500">Voice preset selected — cloned voice.</p>
            )}
            <OpenGroupConfigLink />
          </div>
        ) : (
          <>
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
                <p className="text-[11px] text-zinc-400">
                  프리셋 미선택 시, 스타일 텍스트로 음성을 생성합니다.
                </p>
              </div>
            )}

            {voicePresetId && (
              <p className="text-[11px] text-indigo-500">
                Voice preset selected — all scenes will use the same cloned voice.
              </p>
            )}
          </>
        )}

        <div className="flex items-center gap-2">
          <span className="text-[11px] whitespace-nowrap text-zinc-500">
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

/** Link to open GroupConfigEditor (SSOT for narrator voice preset) */
function OpenGroupConfigLink() {
  return (
    <button
      type="button"
      onClick={() => useUIStore.getState().openGroupConfig()}
      className="text-[11px] font-medium text-zinc-400 transition hover:text-zinc-600"
    >
      시리즈 설정에서 변경 →
    </button>
  );
}
