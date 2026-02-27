"use client";

import { Mic } from "lucide-react";
import type { VoicePreset } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";

type Props = {
  preset: VoicePreset;
  audioPlayer: AudioPlayer;
};

export default function StageVoiceCard({ preset, audioPlayer }: Props) {
  const { playingUrl, play } = audioPlayer;
  const isMe = playingUrl === preset.audio_url;

  return (
    <div className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-white p-3 shadow-sm">
      {/* Icon */}
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-violet-50">
        <Mic className="h-5 w-5 text-violet-500" />
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-zinc-900">{preset.name}</p>
        {preset.voice_design_prompt && (
          <p className="mt-0.5 truncate text-[11px] text-zinc-400">{preset.voice_design_prompt}</p>
        )}
        <div className="mt-1 flex flex-wrap gap-1">
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-500">
            {preset.language}
          </span>
          {preset.is_system && (
            <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] text-blue-600">
              System
            </span>
          )}
        </div>
      </div>

      {/* Play button */}
      {preset.audio_url && (
        <button
          onClick={() => play(preset.audio_url!)}
          className="shrink-0 rounded-lg border border-zinc-200 bg-white px-2.5 py-2 text-xs text-zinc-600 transition hover:bg-zinc-50"
          title={isMe ? "Stop" : "Preview"}
        >
          {isMe ? "\u25A0" : "\u25B6"}
        </button>
      )}
    </div>
  );
}
