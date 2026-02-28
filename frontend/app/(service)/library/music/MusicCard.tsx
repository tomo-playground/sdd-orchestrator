"use client";

import { Play, Square, Sparkles, Pencil, Trash2 } from "lucide-react";
import type { MusicPreset } from "../../../types";

type MusicCardProps = {
  preset: MusicPreset;
  onEdit: (p: MusicPreset) => void;
  onDelete: (p: MusicPreset) => void;
  onPreview: (p: MusicPreset) => void;
  isPlaying: boolean;
  isGenerating: boolean;
};

export default function MusicCard({
  preset,
  onEdit,
  onDelete,
  onPreview,
  isPlaying,
  isGenerating,
}: MusicCardProps) {
  const label = isGenerating
    ? "Generating..."
    : preset.audio_url
      ? isPlaying
        ? "Stop"
        : "Play"
      : "Generate";

  const icon = isGenerating ? (
    <Sparkles className="h-3 w-3 animate-pulse" />
  ) : preset.audio_url ? (
    isPlaying ? (
      <Square className="h-3 w-3" />
    ) : (
      <Play className="h-3 w-3" />
    )
  ) : (
    <Sparkles className="h-3 w-3" />
  );

  return (
    <div className="group relative flex flex-col gap-2 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm transition hover:shadow-md">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-zinc-900">{preset.name}</span>
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

      {/* Prompt */}
      {preset.prompt && (
        <p className="line-clamp-1 text-[12px] text-zinc-400 italic">{preset.prompt}</p>
      )}

      {/* Footer */}
      <div className="mt-auto flex items-center justify-between pt-1">
        <span className="text-[12px] text-zinc-400">
          {preset.duration ? `${preset.duration}s` : ""}
        </span>
        <div className="flex items-center gap-1.5">
          {/* Play / Stop / Generate */}
          <button
            onClick={() => onPreview(preset)}
            disabled={isGenerating || !preset.prompt?.trim()}
            className={`flex items-center gap-1 rounded-full border px-2.5 py-1 text-[12px] font-medium transition disabled:opacity-40 ${
              preset.audio_url
                ? "border-zinc-200 text-zinc-600 hover:bg-zinc-100"
                : "border-indigo-200 text-indigo-600 hover:bg-indigo-50"
            }`}
            title={label}
          >
            {icon}
            <span>{label}</span>
          </button>

          {/* Edit */}
          <button
            onClick={() => onEdit(preset)}
            className="rounded-full border border-zinc-200 p-1.5 text-zinc-500 transition hover:bg-zinc-100"
            title="Edit"
          >
            <Pencil className="h-3 w-3" />
          </button>

          {/* Delete */}
          <button
            onClick={() => onDelete(preset)}
            className="rounded-full border border-red-200 p-1.5 text-red-400 transition hover:bg-red-50"
            title="Delete"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
