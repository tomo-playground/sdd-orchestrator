"use client";

import { useState, useMemo } from "react";
import { Search } from "lucide-react";
import type { LoRA, ActorGender } from "../../../../../types";
import type { WizardLoRA } from "../wizardReducer";
import { FORM_INPUT_COMPACT_CLASSES } from "../../../../../components/ui/variants";
import LoraCard from "../components/LoraCard";

type LoraStepProps = {
  allLoras: LoRA[];
  selectedLoras: WizardLoRA[];
  gender: ActorGender;
  styleBaseModel?: string | null;
  /** LoRA IDs already applied by StyleProfile — hidden from selection */
  excludeLoraIds?: number[];
  onToggleLora: (loraId: number, defaultWeight: number) => void;
  onUpdateWeight: (loraId: number, weight: number) => void;
};

export default function LoraStep({
  allLoras,
  selectedLoras,
  gender,
  styleBaseModel,
  excludeLoraIds,
  onToggleLora,
  onUpdateWeight,
}: LoraStepProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const excludeSet = useMemo(() => new Set(excludeLoraIds ?? []), [excludeLoraIds]);

  const hasCharacterLoras = useMemo(
    () => allLoras.some((l) => l.lora_type === "character"),
    [allLoras]
  );

  const filteredLoras = useMemo(() => {
    return allLoras.filter((lora) => {
      // Only show character-type LoRAs (style/detail are managed by StyleProfile)
      if (lora.lora_type !== "character") return false;

      // Exclude LoRAs already applied by StyleProfile (safety net)
      if (excludeSet.has(lora.id)) return false;

      // Base model compatibility: skip LoRAs incompatible with the selected style
      if (styleBaseModel && lora.base_model && lora.base_model !== styleBaseModel) return false;

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
  }, [allLoras, excludeSet, gender, styleBaseModel, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-800">Character LoRA</h2>
        <p className="mt-0.5 text-xs text-zinc-400">
          캐릭터 고유 외형을 부여할 LoRA를 선택하세요. 화풍 LoRA는 시리즈 설정에서 관리됩니다.
        </p>
      </div>

      {/* Search */}
      {hasCharacterLoras && (
        <div className="relative w-48">
          <Search className="absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`${FORM_INPUT_COMPACT_CLASSES} py-1.5 pl-8 text-xs`}
          />
        </div>
      )}

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
                weight={sel?.weight ?? lora.default_weight}
                onToggle={() => onToggleLora(lora.id, lora.default_weight ?? 0.7)}
                onWeightChange={(w) => onUpdateWeight(lora.id, w)}
              />
            );
          })}
        </div>
      ) : (
        <div className="flex items-center justify-center rounded-xl border border-dashed border-zinc-200 py-12">
          <p className="text-sm text-zinc-400">사용 가능한 캐릭터 LoRA가 없습니다</p>
        </div>
      )}

      {/* Selected indicator */}
      {selectedLoras.length > 0 && <p className="text-xs text-zinc-500">1 LoRA selected</p>}
    </div>
  );
}
