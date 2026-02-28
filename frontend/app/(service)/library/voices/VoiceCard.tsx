"use client";

import { Play, Pencil, Trash2 } from "lucide-react";
import type { VoicePreset } from "../../../types";

type VoiceCardProps = {
  preset: VoicePreset;
  onPlay: (url: string) => void;
  onEdit: (p: VoicePreset) => void;
  onDelete: (p: VoicePreset) => void;
};

export default function VoiceCard({ preset, onPlay, onEdit, onDelete }: VoiceCardProps) {
  return (
    <div className="group relative flex flex-col gap-2 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm transition hover:shadow-md">
      {/* Header row */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-zinc-900">{preset.name}</span>
        <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-500">
          {preset.source_type}
        </span>
        {preset.is_system && (
          <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-500">
            System
          </span>
        )}
      </div>

      {/* Description */}
      {preset.description && (
        <p className="line-clamp-2 text-xs text-zinc-500">{preset.description}</p>
      )}

      {/* Voice design prompt summary */}
      {preset.voice_design_prompt && (
        <p className="line-clamp-1 text-[12px] text-zinc-400 italic">
          {preset.voice_design_prompt}
        </p>
      )}

      {/* Footer */}
      <div className="mt-auto flex items-center justify-between pt-1">
        <span className="text-[12px] text-zinc-400">{preset.language}</span>
        <div className="flex items-center gap-1.5">
          {preset.audio_url && (
            <button
              onClick={() => onPlay(preset.audio_url!)}
              className="rounded-full border border-zinc-200 p-1.5 text-zinc-500 transition hover:bg-zinc-100"
              title="Play"
            >
              <Play className="h-3 w-3" />
            </button>
          )}
          <button
            onClick={() => onEdit(preset)}
            className="rounded-full border border-zinc-200 p-1.5 text-zinc-500 transition hover:bg-zinc-100"
            title="Edit"
          >
            <Pencil className="h-3 w-3" />
          </button>
          {!preset.is_system && (
            <button
              onClick={() => onDelete(preset)}
              className="rounded-full border border-red-200 p-1.5 text-red-400 transition hover:bg-red-50"
              title="Delete"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
