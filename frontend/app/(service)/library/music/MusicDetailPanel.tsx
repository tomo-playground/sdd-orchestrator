"use client";

import { Play, Square, Sparkles, Pencil, Trash2 } from "lucide-react";
import type { MusicPreset } from "../../../types";
import type { EditingMusic } from "../../../hooks/useMusic";
import Button from "../../../components/ui/Button";
import MusicEditForm from "./MusicEditForm";

type Props = {
  /** Preset to display. Omit for create mode. */
  preset?: MusicPreset;
  /** Non-null when form is active for this panel. */
  editing: EditingMusic | null;
  saving?: boolean;
  previewing?: boolean;
  previewUrl?: string | null;
  playingId?: number | null;
  previewingId?: number | null;
  onEdit?: () => void;
  onDelete?: () => void;
  onSave: () => void;
  onCancel: () => void;
  onPreview: () => void;
  onPlayAudio: (url: string, presetId?: number) => void;
  onPreviewPreset?: (p: MusicPreset) => void;
  onSet: <K extends keyof EditingMusic>(key: K, value: EditingMusic[K]) => void;
};

export default function MusicDetailPanel({
  preset,
  editing,
  saving,
  previewing,
  previewUrl,
  playingId,
  previewingId,
  onEdit,
  onDelete,
  onSave,
  onCancel,
  onPreview,
  onPlayAudio,
  onPreviewPreset,
  onSet,
}: Props) {
  if (editing) {
    return (
      <MusicEditForm
        editing={editing}
        isCreate={!preset}
        saving={saving}
        previewing={previewing}
        previewUrl={previewUrl}
        onSave={onSave}
        onCancel={onCancel}
        onPreview={onPreview}
        onPlayAudio={onPlayAudio}
        onSet={onSet}
      />
    );
  }

  // ── View mode (preset must exist) ──────────────────
  if (!preset) return null;

  const isPlaying = playingId === preset.id;
  const isGenerating = previewingId === preset.id;

  return (
    <div className="space-y-5 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-bold text-zinc-900">{preset.name}</h2>
          {preset.is_system && (
            <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-500">
              System
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onEdit && (
            <button
              onClick={onEdit}
              className="rounded-lg border border-zinc-200 p-2 text-zinc-500 transition hover:bg-zinc-100"
              title="Edit"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="rounded-lg border border-red-200 p-2 text-red-400 transition hover:bg-red-50"
              title="Delete"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Description */}
      {preset.description && <p className="text-sm text-zinc-600">{preset.description}</p>}

      {/* Prompt */}
      {preset.prompt && (
        <div>
          <span className="text-xs font-medium text-zinc-400">Prompt</span>
          <p className="mt-1 text-sm text-zinc-500 italic">{preset.prompt}</p>
        </div>
      )}

      {/* Info */}
      <div className="flex gap-6 text-xs text-zinc-400">
        {preset.duration != null && <span>Duration: {preset.duration}s</span>}
        {preset.seed != null && <span>Seed: {preset.seed}</span>}
      </div>

      {/* Audio */}
      <div className="flex items-center gap-2">
        {preset.audio_url ? (
          <Button
            size="sm"
            variant={isPlaying ? "outline" : "gradient"}
            onClick={() => onPreviewPreset?.(preset)}
            disabled={isGenerating}
          >
            {isPlaying ? (
              <Square className="mr-1.5 h-3 w-3" />
            ) : (
              <Play className="mr-1.5 h-3 w-3" />
            )}
            {isPlaying ? "정지" : "재생"}
          </Button>
        ) : (
          <Button
            size="sm"
            variant="gradient"
            onClick={() => onPreviewPreset?.(preset)}
            disabled={isGenerating || !preset.prompt?.trim()}
            loading={isGenerating}
          >
            <Sparkles className="mr-1.5 h-3 w-3" />
            {isGenerating ? "생성 중..." : "BGM 생성"}
          </Button>
        )}
      </div>
    </div>
  );
}
