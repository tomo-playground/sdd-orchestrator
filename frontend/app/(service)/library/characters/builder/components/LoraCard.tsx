"use client";

import Image from "next/image";
import type { LoRA } from "../../../../../types";
import { resolveImageUrl } from "../../../../../utils/url";
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
  const thumbUrl = resolveImageUrl(lora.preview_image_url);
  const displayName = lora.display_name || lora.name;
  const triggerText = lora.trigger_words?.join(", ") ?? "";

  return (
    <div
      className={`flex flex-col overflow-hidden rounded-lg border transition ${
        isSelected
          ? "border-2 border-zinc-900 shadow-sm"
          : "border border-zinc-200 hover:border-zinc-300"
      }`}
    >
      {/* Thumbnail */}
      <div className="relative aspect-[3/2] bg-zinc-100">
        {thumbUrl ? (
          <Image
            src={thumbUrl}
            alt={displayName}
            fill
            className="object-cover"
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            unoptimized
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <span className="text-2xl font-bold text-zinc-300">
              {displayName.charAt(0).toUpperCase()}
            </span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex flex-1 flex-col gap-1.5 p-2.5">
        <p className="truncate text-sm font-medium text-zinc-800">{displayName}</p>

        {lora.lora_type && (
          <Badge variant={lora.lora_type === "character" ? "info" : "default"} size="sm">
            {lora.lora_type}
          </Badge>
        )}

        {triggerText && (
          <p className="line-clamp-1 text-[11px] text-zinc-400">trigger: {triggerText}</p>
        )}

        {/* Weight slider */}
        <div className={`mt-1 ${!isSelected ? "pointer-events-none opacity-40" : ""}`}>
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
          className="mt-1 w-full text-xs"
          onClick={onToggle}
        >
          {isSelected ? "Added" : "+ Add"}
        </Button>
      </div>
    </div>
  );
}
