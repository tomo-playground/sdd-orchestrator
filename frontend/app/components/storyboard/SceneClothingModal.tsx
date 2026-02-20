"use client";

import { useState } from "react";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import type { Scene } from "../../types";

type SceneClothingModalProps = {
  scene: Scene;
  onClose: () => void;
  onSave: (clothingTags: Record<string, string[]> | null) => void;
  showToast: (message: string, type: "success" | "error") => void;
};

const CLOTHING_PRESETS = [
  "school_uniform",
  "serafuku",
  "white_dress",
  "black_dress",
  "maid_headdress, maid_apron",
  "hoodie",
  "business_suit",
  "kimono",
];

export default function SceneClothingModal({
  scene,
  onClose,
  onSave,
  showToast,
}: SceneClothingModalProps) {
  const trapRef = useFocusTrap(true);
  const existing = scene.clothing_tags ?? {};
  const defaultCharKey = Object.keys(existing)[0] ?? "default";
  const defaultTags = existing[defaultCharKey] ?? [];
  const [tagInput, setTagInput] = useState(defaultTags.join(", "));

  const handleSave = () => {
    const trimmed = tagInput.trim();
    if (!trimmed) {
      onSave(null);
      onClose();
      return;
    }
    const tags = trimmed
      .split(",")
      .map((t) => t.trim().replace(/\s+/g, "_"))
      .filter(Boolean);
    if (tags.length === 0) {
      onSave(null);
      onClose();
      return;
    }
    onSave({ [defaultCharKey]: tags });
    onClose();
  };

  const handleReset = () => {
    setTagInput("");
    onSave(null);
    showToast("기본 의상으로 리셋되었습니다", "success");
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="clothing-modal-title"
    >
      <div
        ref={trapRef}
        tabIndex={-1}
        className="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl outline-none"
      >
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h3 id="clothing-modal-title" className="text-lg font-semibold text-zinc-800">
            의상 변경
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
          >
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          <p className="text-sm text-zinc-600">
            Danbooru 태그 형식으로 의상을 지정합니다. 쉼표(,)로 구분하세요.
          </p>

          {/* Presets */}
          <div className="flex flex-wrap gap-2">
            {CLOTHING_PRESETS.map((preset) => (
              <button
                key={preset}
                type="button"
                onClick={() => {
                  const current = tagInput.trim();
                  setTagInput(current ? `${current}, ${preset}` : preset);
                }}
                className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs text-zinc-600 transition hover:border-amber-300 hover:bg-amber-50"
              >
                {preset.replace(/_/g, " ")}
              </button>
            ))}
          </div>

          {/* Tag input */}
          <div>
            <label htmlFor="clothing-tags" className="mb-1 block text-sm font-semibold text-zinc-700">
              의상 태그
            </label>
            <textarea
              id="clothing-tags"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              placeholder="예: school_uniform, white_shirt, pleated_skirt"
              className="w-full rounded-xl border border-zinc-200 bg-white/80 px-4 py-3 text-sm outline-none focus:border-amber-400"
              rows={2}
            />
            <p className="mt-1 text-[12px] text-zinc-400">
              공백은 자동으로 언더바(_)로 변환됩니다
            </p>
          </div>

          {/* Current tags preview */}
          {tagInput.trim() && (
            <div className="flex flex-wrap gap-1.5">
              {tagInput
                .split(",")
                .map((t) => t.trim())
                .filter(Boolean)
                .map((tag, i) => (
                  <span
                    key={i}
                    className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[12px] font-medium text-amber-700"
                  >
                    {tag.replace(/\s+/g, "_")}
                  </span>
                ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleReset}
              className="rounded-full border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
            >
              기본 의상으로 리셋
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="flex-1 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:from-amber-600 hover:to-orange-600"
            >
              저장
            </button>
          </div>

          <p className="text-[12px] text-zinc-400">
            의상 변경 후 이미지를 재생성하면 반영됩니다.
          </p>
        </div>
      </div>
    </div>
  );
}
