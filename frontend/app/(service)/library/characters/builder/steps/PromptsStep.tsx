"use client";

import { useMemo } from "react";
import type { PromptField } from "../wizardReducer";
import { findDuplicateTokens } from "../../shared/promptDuplicateCheck";
import { formatTagName } from "../../shared/formatTag";
import PromptPair from "../../shared/PromptPair";

type PromptsStepProps = {
  customBasePrompt: string;
  customNegativePrompt: string;
  referenceBasePrompt: string;
  referenceNegativePrompt: string;
  selectedTagNames?: string[];
  onFieldChange: (field: PromptField, value: string) => void;
};

export default function PromptsStep({
  customBasePrompt,
  customNegativePrompt,
  referenceBasePrompt,
  referenceNegativePrompt,
  selectedTagNames = [],
  onFieldChange,
}: PromptsStepProps) {
  const duplicates = useMemo(
    () => findDuplicateTokens(customBasePrompt, selectedTagNames),
    [customBasePrompt, selectedTagNames]
  );

  return (
    <div className="space-y-5">
      <PromptPair
        label="Custom (appended to auto-generated tags)"
        positiveValue={customBasePrompt}
        negativeValue={customNegativePrompt}
        onPositiveChange={(v) => onFieldChange("scene_positive_prompt", v)}
        onNegativeChange={(v) => onFieldChange("scene_negative_prompt", v)}
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
        onPositiveChange={(v) => onFieldChange("reference_positive_prompt", v)}
        onNegativeChange={(v) => onFieldChange("reference_negative_prompt", v)}
        positivePlaceholder="e.g. masterpiece, best quality, anime portrait, looking at viewer, clean background"
        negativePlaceholder="e.g. lowres, bad anatomy, multiple views, ..."
      />
    </div>
  );
}
