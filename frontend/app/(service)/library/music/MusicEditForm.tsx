"use client";

import type { EditingMusic } from "../../../hooks/useMusic";
import Button from "../../../components/ui/Button";
import {
  FORM_INPUT_COMPACT_CLASSES,
  FORM_LABEL_COMPACT_CLASSES,
} from "../../../components/ui/variants";

type Props = {
  editing: EditingMusic;
  isCreate: boolean;
  saving?: boolean;
  previewing?: boolean;
  previewUrl?: string | null;
  onSave: () => void;
  onCancel: () => void;
  onPreview: () => void;
  onPlayAudio: (url: string, presetId?: number) => void;
  onSet: <K extends keyof EditingMusic>(key: K, value: EditingMusic[K]) => void;
};

export default function MusicEditForm({
  editing,
  isCreate,
  saving,
  previewing,
  previewUrl,
  onSave,
  onCancel,
  onPreview,
  onPlayAudio,
  onSet,
}: Props) {
  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-zinc-700">
          {isCreate ? "새 BGM 프리셋" : "프리셋 수정"}
        </h2>
        <Button
          onClick={onCancel}
          variant="ghost"
          size="sm"
          className="px-0 text-zinc-400 hover:bg-transparent hover:text-zinc-600"
        >
          취소
        </Button>
      </div>

      <div className="space-y-3">
        <div>
          <label className={FORM_LABEL_COMPACT_CLASSES}>Name *</label>
          <input
            value={editing.name}
            onChange={(e) => onSet("name", e.target.value)}
            className={FORM_INPUT_COMPACT_CLASSES}
            placeholder="프리셋 이름 (예: Lo-fi Chill)"
          />
        </div>
        <div>
          <label className={FORM_LABEL_COMPACT_CLASSES}>Description</label>
          <input
            value={editing.description}
            onChange={(e) => onSet("description", e.target.value)}
            className={FORM_INPUT_COMPACT_CLASSES}
            placeholder="선택 사항"
          />
        </div>
        <div>
          <label className={FORM_LABEL_COMPACT_CLASSES}>Prompt *</label>
          <input
            value={editing.prompt}
            onChange={(e) => onSet("prompt", e.target.value)}
            className={FORM_INPUT_COMPACT_CLASSES}
            placeholder="예: ambient lo-fi hip hop, soft piano"
          />
        </div>
        <div className="flex items-end gap-3">
          <div className="w-28">
            <label className={FORM_LABEL_COMPACT_CLASSES}>Duration (sec)</label>
            <input
              type="number"
              min={5}
              max={47}
              step={1}
              value={editing.duration}
              onChange={(e) => onSet("duration", Number(e.target.value))}
              className={FORM_INPUT_COMPACT_CLASSES}
            />
          </div>
          <Button
            size="sm"
            variant="gradient"
            onClick={onPreview}
            disabled={previewing || !editing.prompt?.trim()}
            loading={previewing}
          >
            Preview
          </Button>
          {previewUrl && (
            <Button size="sm" variant="outline" onClick={() => onPlayAudio(previewUrl)}>
              재생
            </Button>
          )}
        </div>
      </div>

      <div className="flex justify-end pt-2">
        <Button
          size="sm"
          onClick={onSave}
          disabled={saving || !editing.name.trim()}
          loading={saving}
        >
          {isCreate ? "생성" : "저장"}
        </Button>
      </div>
    </div>
  );
}
