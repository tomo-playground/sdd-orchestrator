"use client";

import { useMemo } from "react";
import type { PromptField } from "../wizardReducer";
import { findDuplicateTokens } from "../../shared/promptDuplicateCheck";
import { formatTagName } from "../../shared/formatTag";
import PromptPair from "../../shared/PromptPair";

type PromptsStepProps = {
  positivePrompt: string;
  negativePrompt: string;
  selectedTagNames?: string[];
  onFieldChange: (field: PromptField, value: string) => void;
};

export default function PromptsStep({
  positivePrompt,
  negativePrompt,
  selectedTagNames = [],
  onFieldChange,
}: PromptsStepProps) {
  const duplicates = useMemo(
    () => findDuplicateTokens(positivePrompt, selectedTagNames),
    [positivePrompt, selectedTagNames]
  );

  return (
    <div className="space-y-5">
      <PromptPair
        label="캐릭터 프롬프트 (씬·레퍼런스 공통 적용)"
        positiveValue={positivePrompt}
        negativeValue={negativePrompt}
        onPositiveChange={(v) => onFieldChange("positive_prompt", v)}
        onNegativeChange={(v) => onFieldChange("negative_prompt", v)}
        positivePlaceholder="DB 태그에 없는 추가 보정 태그 (선택사항)"
        negativePlaceholder="e.g. (red_sweater:1.3), (wings:1.3), very_long_hair, ..."
      />
      {duplicates.length > 0 && (
        <p className="text-[11px] text-amber-600">
          {duplicates.length} tag{duplicates.length > 1 ? "s" : ""} already in Appearance:{" "}
          {duplicates.map((d) => formatTagName(d)).join(", ")}
        </p>
      )}
    </div>
  );
}
