"use client";

import { Play, Pencil, Trash2 } from "lucide-react";
import type { VoicePreset } from "../../../types";
import type { EditingPreset } from "../../../hooks/useVoicePresets";
import Button from "../../../components/ui/Button";
import VoiceEditForm from "./VoiceEditForm";

type Props = {
  /** Preset to display. Omit for create mode. */
  preset?: VoicePreset;
  /** Non-null when form is active for this panel. */
  editing: EditingPreset | null;
  saving?: boolean;
  previewing?: boolean;
  previewUrl?: string | null;
  onEdit?: () => void;
  onDelete?: () => void;
  onSave: () => void;
  onCancel: () => void;
  onPreview: () => void;
  onPlayAudio: (url: string) => void;
  onSet: <K extends keyof EditingPreset>(key: K, value: EditingPreset[K]) => void;
};

export default function VoiceDetailPanel({
  preset,
  editing,
  saving,
  previewing,
  previewUrl,
  onEdit,
  onDelete,
  onSave,
  onCancel,
  onPreview,
  onPlayAudio,
  onSet,
}: Props) {
  if (editing) {
    return (
      <VoiceEditForm
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
          {onDelete && !preset.is_system && (
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

      {/* Voice Design Prompt */}
      {preset.voice_design_prompt && (
        <div>
          <span className="text-xs font-medium text-zinc-400">Voice Design Prompt</span>
          <p className="mt-1 text-sm text-zinc-500 italic">{preset.voice_design_prompt}</p>
        </div>
      )}

      {/* Info */}
      <div className="flex gap-6 text-xs text-zinc-400">
        <span>Language: {preset.language}</span>
        {preset.voice_seed != null && <span>Seed: {preset.voice_seed}</span>}
      </div>

      {/* Audio */}
      {preset.audio_url && (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="gradient"
            onClick={() => onPlayAudio(preset.audio_url!)}
          >
            <Play className="mr-1.5 h-3 w-3" />
            재생
          </Button>
        </div>
      )}
    </div>
  );
}
