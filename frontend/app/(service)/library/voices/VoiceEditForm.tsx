"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import type { EditingPreset } from "../../../hooks/useVoicePresets";
import Button from "../../../components/ui/Button";
import { API_BASE } from "../../../constants";
import {
  FORM_INPUT_COMPACT_CLASSES,
  FORM_LABEL_COMPACT_CLASSES,
} from "../../../components/ui/variants";

type Props = {
  editing: EditingPreset;
  isCreate: boolean;
  saving?: boolean;
  previewing?: boolean;
  previewUrl?: string | null;
  onSave: () => void;
  onCancel: () => void;
  onPreview: () => void;
  onPlayAudio: (url: string) => void;
  onSet: <K extends keyof EditingPreset>(key: K, value: EditingPreset[K]) => void;
};

export default function VoiceEditForm({
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
  const [languages, setLanguages] = useState<{ value: string; label: string }[]>([]);

  useEffect(() => {
    axios
      .get(`${API_BASE}/presets`)
      .then((res) => {
        if (Array.isArray(res.data?.languages)) setLanguages(res.data.languages);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-zinc-700">
          {isCreate ? "새 음성 프리셋" : "프리셋 수정"}
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
            placeholder="프리셋 이름"
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
          <label className={FORM_LABEL_COMPACT_CLASSES}>Voice Design Prompt *</label>
          <input
            value={editing.voice_design_prompt}
            onChange={(e) => onSet("voice_design_prompt", e.target.value)}
            className={FORM_INPUT_COMPACT_CLASSES}
            placeholder="예: calm 40s female narrator"
          />
        </div>
        <div>
          <label className={FORM_LABEL_COMPACT_CLASSES}>Sample Text</label>
          <input
            value={editing.sample_text}
            onChange={(e) => onSet("sample_text", e.target.value)}
            className={FORM_INPUT_COMPACT_CLASSES}
            placeholder="미리 듣기용 텍스트"
          />
        </div>
        <div className="flex items-end gap-3">
          <div className="w-40">
            <label className={FORM_LABEL_COMPACT_CLASSES}>Language</label>
            <select
              value={editing.language}
              onChange={(e) => onSet("language", e.target.value)}
              className={FORM_INPUT_COMPACT_CLASSES}
            >
              {languages.length === 0 && (
                <option value={editing.language}>{editing.language}</option>
              )}
              {languages.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>
          <Button
            size="sm"
            variant="gradient"
            onClick={onPreview}
            disabled={previewing || !editing.voice_design_prompt?.trim()}
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
