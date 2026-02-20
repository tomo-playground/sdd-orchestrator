"use client";

import { useMemo } from "react";
import type { PromptMode } from "../../../../types";
import type { PromptField } from "../wizardReducer";
import { findDuplicateTokens } from "../../shared/promptDuplicateCheck";
import { formatTagName } from "../../shared/formatTag";
import PromptPair from "../../shared/PromptPair";

type PromptsStepProps = {
  promptMode: PromptMode;
  customBasePrompt: string;
  customNegativePrompt: string;
  referenceBasePrompt: string;
  referenceNegativePrompt: string;
  selectedTagNames?: string[];
  onModeChange: (mode: PromptMode) => void;
  onFieldChange: (field: PromptField, value: string) => void;
};

export default function PromptsStep({
  promptMode,
  customBasePrompt,
  customNegativePrompt,
  referenceBasePrompt,
  referenceNegativePrompt,
  selectedTagNames = [],
  onModeChange,
  onFieldChange,
}: PromptsStepProps) {
  const duplicates = useMemo(
    () => findDuplicateTokens(customBasePrompt, selectedTagNames),
    [customBasePrompt, selectedTagNames],
  );

  return (
    <div className="space-y-5">
      <div>
        <label className="mb-1 block text-xs font-medium text-zinc-500">Prompt Mode</label>
        <div className="flex gap-2">
          {(["auto", "standard", "lora"] as PromptMode[]).map((m) => (
            <button
              key={m}
              onClick={() => onModeChange(m)}
              className={`rounded-full px-4 py-1.5 text-xs font-medium capitalize transition ${
                promptMode === m
                  ? "bg-zinc-900 text-white"
                  : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <hr className="border-zinc-100" />

      <PromptPair
        label="Custom (appended to auto-generated tags)"
        positiveValue={customBasePrompt}
        negativeValue={customNegativePrompt}
        onPositiveChange={(v) => onFieldChange("custom_base_prompt", v)}
        onNegativeChange={(v) => onFieldChange("custom_negative_prompt", v)}
        positivePlaceholder="e.g. masterpiece, best quality, ..."
        negativePlaceholder="e.g. lowres, bad anatomy, ..."
      />
      {duplicates.length > 0 && (
        <p className="text-[11px] text-amber-600">
          {duplicates.length} tag{duplicates.length > 1 ? "s" : ""} already in Appearance:{" "}
          {duplicates.map((d) => formatTagName(d)).join(", ")}
        </p>
      )}

      <hr className="border-zinc-100" />

      <PromptPair
        label="Reference (IP-Adapter 레퍼런스 이미지 생성용)"
        positiveValue={referenceBasePrompt}
        negativeValue={referenceNegativePrompt}
        onPositiveChange={(v) => onFieldChange("reference_base_prompt", v)}
        onNegativeChange={(v) => onFieldChange("reference_negative_prompt", v)}
        positivePlaceholder="e.g. masterpiece, best quality, anime portrait, looking at viewer, clean background"
        negativePlaceholder="e.g. lowres, bad anatomy, multiple views, ..."
      />
    </div>
  );
}
