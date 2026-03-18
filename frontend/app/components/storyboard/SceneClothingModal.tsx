"use client";

import { useState } from "react";
import type { Scene } from "../../types";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import CloseButton from "./CloseButton";
import TagAutocomplete from "../ui/TagAutocomplete";
import useTagValidationDebounced from "../../hooks/useTagValidationDebounced";
import TagValidationWarning from "../prompt/TagValidationWarning";

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
  const existing = scene.clothing_tags ?? {};
  const defaultCharKey = Object.keys(existing)[0] ?? "default";
  const defaultTags = existing[defaultCharKey] ?? [];
  const [tagInput, setTagInput] = useState(defaultTags.join(", "));

  const { validationResult, handleAutoReplace, clearValidation } = useTagValidationDebounced(
    tagInput,
    setTagInput
  );

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
    <Modal open onClose={onClose} size="lg" ariaLabelledBy="clothing-modal-title">
      <Modal.Header>
        <h3 id="clothing-modal-title" className="text-lg font-semibold text-zinc-800">
          의상 변경
        </h3>
        <CloseButton onClick={onClose} />
      </Modal.Header>

      <div className="p-6 space-y-4">
        <p className="text-sm text-zinc-600">
          Danbooru 태그 형식으로 의상을 지정합니다. 쉼표(,)로 구분하세요.
        </p>

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

        <div>
          <label htmlFor="clothing-tags" className="mb-1 block text-sm font-semibold text-zinc-700">
            의상 태그
          </label>
          <TagAutocomplete
            id="clothing-tags"
            value={tagInput}
            onChange={setTagInput}
            placeholder="예: school_uniform, white_shirt, pleated_skirt"
            className="w-full rounded-xl border border-zinc-200 bg-white/80 px-4 py-3 text-sm outline-none focus:border-amber-400"
            rows={2}
          />
          <TagValidationWarning
            result={validationResult}
            onAutoReplace={handleAutoReplace}
            onDismiss={clearValidation}
          />
          <p className="mt-1 text-[12px] text-zinc-400">공백은 자동으로 언더바(_)로 변환됩니다</p>
        </div>

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

        <p className="text-[12px] text-zinc-400">의상 변경 후 이미지를 재생성하면 반영됩니다.</p>
      </div>

      <Modal.Footer>
        <Button variant="secondary" onClick={handleReset}>
          기본 의상으로 리셋
        </Button>
        <Button variant="primary" onClick={handleSave}>
          저장
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
