"use client";

import { useState, useMemo } from "react";
import { Search } from "lucide-react";
import type { LoRA, ActorGender } from "../../../../../types";
import type { WizardLoRA } from "../wizardReducer";
import {
  FILTER_PILL_ACTIVE,
  FILTER_PILL_INACTIVE,
  FORM_INPUT_COMPACT_CLASSES,
} from "../../../../../components/ui/variants";
import LoraCard from "../components/LoraCard";

type LoraStepProps = {
  allLoras: LoRA[];
  selectedLoras: WizardLoRA[];
  gender: ActorGender;
  styleBaseModel?: string | null;
  onToggleLora: (loraId: number, defaultWeight: number) => void;
  onUpdateWeight: (loraId: number, weight: number) => void;
};

type TypeFilter = "all" | "character" | "style";

const TYPE_OPTIONS: { value: TypeFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "character", label: "Character" },
  { value: "style", label: "Style" },
];

export default function LoraStep({
  allLoras,
  selectedLoras,
  gender,
  styleBaseModel,
  onToggleLora,
  onUpdateWeight,
}: LoraStepProps) {
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("character");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredLoras = useMemo(() => {
    return allLoras.filter((lora) => {
      // Gender filter: show if unlocked or matching
      if (lora.gender_locked && lora.gender_locked !== gender) return false;

      // Base model compatibility: skip LoRAs incompatible with the selected style
      if (styleBaseModel && lora.base_model && lora.base_model !== styleBaseModel) return false;

      // Type filter
      if (typeFilter !== "all" && lora.lora_type !== typeFilter) return false;

      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const name = (lora.display_name || lora.name).toLowerCase();
        const triggers = (lora.trigger_words ?? []).join(" ").toLowerCase();
        if (!name.includes(q) && !lora.name.toLowerCase().includes(q) && !triggers.includes(q)) {
          return false;
        }
      }

      return true;
    });
  }, [allLoras, gender, styleBaseModel, typeFilter, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-800">Select LoRAs</h2>
        <p className="mt-0.5 text-xs text-zinc-400">
          Optional. Choose character or style LoRAs to apply.
        </p>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Type pills */}
        {TYPE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setTypeFilter(opt.value)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              typeFilter === opt.value ? FILTER_PILL_ACTIVE : FILTER_PILL_INACTIVE
            }`}
          >
            {opt.label}
          </button>
        ))}

        {/* Search input */}
        <div className="relative ml-auto w-48">
          <Search className="absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`${FORM_INPUT_COMPACT_CLASSES} py-1.5 pl-8 text-xs`}
          />
        </div>
      </div>

      {/* Card grid */}
      {filteredLoras.length > 0 ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {filteredLoras.map((lora) => {
            const sel = selectedLoras.find((s) => s.loraId === lora.id);
            return (
              <LoraCard
                key={lora.id}
                lora={lora}
                isSelected={!!sel}
                weight={sel?.weight ?? lora.optimal_weight ?? lora.default_weight}
                onToggle={() =>
                  onToggleLora(lora.id, lora.optimal_weight ?? lora.default_weight ?? 0.7)
                }
                onWeightChange={(w) => onUpdateWeight(lora.id, w)}
              />
            );
          })}
        </div>
      ) : (
        <div className="flex items-center justify-center rounded-xl border border-dashed border-zinc-200 py-12">
          <p className="text-sm text-zinc-400">No LoRAs match the current filter</p>
        </div>
      )}

      {/* Selected count */}
      {selectedLoras.length > 0 && (
        <p className="text-xs text-zinc-500">
          {selectedLoras.length} LoRA{selectedLoras.length !== 1 ? "s" : ""} selected
        </p>
      )}
    </div>
  );
}
