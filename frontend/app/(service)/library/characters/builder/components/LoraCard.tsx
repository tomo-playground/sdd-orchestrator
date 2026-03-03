"use client";

import type { LoRA } from "../../../../../types";
import Badge from "../../../../../components/ui/Badge";
import Button from "../../../../../components/ui/Button";

type LoraCardProps = {
  lora: LoRA;
  isSelected: boolean;
  weight: number;
  onToggle: () => void;
  onWeightChange: (weight: number) => void;
};

export default function LoraCard({
  lora,
  isSelected,
  weight,
  onToggle,
  onWeightChange,
}: LoraCardProps) {
  const displayName = lora.display_name || lora.name;
  const triggerText = lora.trigger_words?.join(", ") ?? "";

  return (
    <div
      className={`flex flex-col rounded-lg border p-3 transition ${
        isSelected
          ? "border-2 border-zinc-900 shadow-sm"
          : "border border-zinc-200 hover:border-zinc-300"
      }`}
    >
      {/* Header: name + badge */}
      <div className="flex items-start justify-between gap-2">
        <p className="truncate text-sm font-medium text-zinc-800">{displayName}</p>
        {lora.lora_type && (
          <Badge variant={lora.lora_type === "character" ? "info" : "default"} size="sm">
            {lora.lora_type}
          </Badge>
        )}
      </div>

      {triggerText && (
        <p className="mt-1 line-clamp-1 text-[11px] text-zinc-400">trigger: {triggerText}</p>
      )}

      {/* Weight slider */}
      <div className={`mt-2 ${!isSelected ? "pointer-events-none opacity-40" : ""}`}>
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-zinc-500">Weight</span>
          <span className="text-[11px] font-medium text-zinc-700">{weight.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={lora.weight_min}
          max={lora.weight_max}
          step={0.05}
          value={weight}
          onChange={(e) => onWeightChange(parseFloat(e.target.value))}
          disabled={!isSelected}
          className="h-1.5 w-full cursor-pointer accent-zinc-900"
        />
      </div>

      {/* Toggle button */}
      <Button
        size="sm"
        variant={isSelected ? "secondary" : "primary"}
        className="mt-2 w-full text-xs"
        onClick={onToggle}
      >
        {isSelected ? "Added" : "+ Add"}
      </Button>
    </div>
  );
}
