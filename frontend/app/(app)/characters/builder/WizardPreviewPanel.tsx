"use client";

import Image from "next/image";
import { Sparkles, UserRound } from "lucide-react";
import type { ActorGender, LoRA } from "../../../types";
import type { WizardTag } from "./steps/AppearanceStep";
import type { WizardLoRA } from "./wizardReducer";
import { WIZARD_CATEGORIES } from "./wizardTemplates";
import Button from "../../../components/ui/Button";

type WizardPreviewPanelProps = {
  name: string;
  gender: ActorGender;
  selectedTags: WizardTag[];
  selectedLoras: WizardLoRA[];
  allLoras: LoRA[];
  previewImage: string | null;
  isGenerating: boolean;
  onGeneratePreview: () => void;
};

export default function WizardPreviewPanel({
  name,
  gender,
  selectedTags,
  selectedLoras,
  allLoras,
  previewImage,
  isGenerating,
  onGeneratePreview,
}: WizardPreviewPanelProps) {
  // Group selected tags by category for summary
  const tagsByCategory = WIZARD_CATEGORIES.map((cat) => ({
    label: cat.label,
    tags: selectedTags.filter((t) => t.groupName === cat.groupName),
  })).filter((g) => g.tags.length > 0);

  const hasSelections = selectedTags.length > 0;

  return (
    <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
      {/* Preview image */}
      <div className="relative flex aspect-[3/4] items-center justify-center overflow-hidden rounded-2xl border border-zinc-200 bg-zinc-50">
        {previewImage ? (
          <Image
            src={`data:image/png;base64,${previewImage}`}
            alt="Character preview"
            fill
            className="object-cover"
            unoptimized
          />
        ) : (
          <div className="text-center">
            <UserRound className="mx-auto h-12 w-12 text-zinc-300" />
            <p className="mt-2 text-xs text-zinc-400">
              {hasSelections ? "Generate a preview" : "Select tags first"}
            </p>
          </div>
        )}
        {isGenerating && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40">
            <div className="text-center">
              <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-white border-t-transparent" />
              <p className="mt-2 text-xs font-medium text-white">Generating...</p>
            </div>
          </div>
        )}
      </div>

      {/* Generate Preview button */}
      {hasSelections && (
        <Button
          size="sm"
          variant="secondary"
          className="w-full"
          onClick={onGeneratePreview}
          loading={isGenerating}
          disabled={isGenerating}
        >
          <Sparkles className="h-3.5 w-3.5" />
          {previewImage ? "Regenerate Preview" : "Generate Preview"}
        </Button>
      )}

      {/* Character info */}
      <div className="rounded-xl border border-zinc-100 bg-white p-3">
        <p className="text-sm font-semibold text-zinc-800">{name || "Unnamed"}</p>
        <p className="text-xs text-zinc-400">{gender === "female" ? "Female" : "Male"}</p>
      </div>

      {/* Tag summary */}
      {tagsByCategory.length > 0 && (
        <div className="rounded-xl border border-zinc-100 bg-white p-3">
          <p className="mb-2 text-[12px] font-semibold tracking-wider text-zinc-500 uppercase">
            Selected Tags
          </p>
          <div className="space-y-2">
            {tagsByCategory.map(({ label, tags }) => (
              <div key={label}>
                <p className="text-[11px] font-medium text-zinc-400">{label}</p>
                <div className="mt-0.5 flex flex-wrap gap-1">
                  {tags.map((t) => (
                    <span
                      key={t.tagId}
                      className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-600"
                    >
                      {t.name.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* LoRA summary */}
      {selectedLoras.length > 0 && (
        <div className="rounded-xl border border-zinc-100 bg-white p-3">
          <p className="mb-2 text-[12px] font-semibold tracking-wider text-zinc-500 uppercase">
            LoRAs
          </p>
          <div className="space-y-1">
            {selectedLoras.map((sl) => {
              const lora = allLoras.find((lr) => lr.id === sl.loraId);
              return (
                <div key={sl.loraId} className="flex items-center justify-between">
                  <span className="truncate text-xs text-zinc-600">
                    {lora?.display_name || lora?.name || `LoRA #${sl.loraId}`}
                  </span>
                  <span className="ml-2 shrink-0 text-[11px] font-medium text-zinc-400">
                    {sl.weight.toFixed(2)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
