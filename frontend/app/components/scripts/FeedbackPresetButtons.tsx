"use client";

import { useState } from "react";
import { Zap, Flame, Mic, Scissors, Pencil } from "lucide-react";
import type { FeedbackPreset } from "../../types";

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  zap: Zap,
  flame: Flame,
  mic: Mic,
  scissors: Scissors,
};

type Props = {
  presets: FeedbackPreset[];
  onPresetSelect: (id: string, params?: Record<string, string>) => void;
  onCustom: () => void;
};

export default function FeedbackPresetButtons({ presets, onPresetSelect, onCustom }: Props) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedParams, setSelectedParams] = useState<Record<string, string>>({});

  const activePreset = presets.find((p) => p.id === activeId);

  const handlePresetClick = (preset: FeedbackPreset) => {
    if (preset.has_params && preset.param_options) {
      setActiveId(activeId === preset.id ? null : preset.id);
      setSelectedParams({});
    } else {
      onPresetSelect(preset.id);
    }
  };

  const handleParamSelect = (key: string, value: string) => {
    const next = { ...selectedParams, [key]: value };
    setSelectedParams(next);

    // All param keys filled → submit
    if (activePreset?.param_options) {
      const allKeys = Object.keys(activePreset.param_options);
      if (allKeys.every((k) => next[k])) {
        onPresetSelect(activePreset.id, next);
        setActiveId(null);
        setSelectedParams({});
      }
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium text-zinc-500">빠른 수정</p>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
        {presets.map((p) => {
          const Icon = ICON_MAP[p.icon] ?? Zap;
          const isActive = activeId === p.id;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => handlePresetClick(p)}
              className={`flex flex-col items-center gap-1 rounded-xl border px-3 py-2.5 text-xs transition-all ${
                isActive
                  ? "border-amber-500 bg-amber-50 text-amber-800"
                  : "border-zinc-200 bg-white text-zinc-600 hover:border-amber-300 hover:bg-amber-50/50"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{p.label}</span>
            </button>
          );
        })}
        <button
          type="button"
          onClick={onCustom}
          className="flex flex-col items-center gap-1 rounded-xl border border-zinc-200 bg-white px-3 py-2.5 text-xs text-zinc-600 transition-all hover:border-zinc-400 hover:bg-zinc-50"
        >
          <Pencil className="h-4 w-4" />
          <span>직접 수정</span>
        </button>
      </div>

      {/* Param options chips */}
      {activePreset?.has_params && activePreset.param_options && (
        <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50/50 p-3">
          {Object.entries(activePreset.param_options).map(([key, values]) => (
            <div key={key}>
              <p className="mb-1.5 text-[11px] font-medium text-amber-700">{key}</p>
              <div className="flex flex-wrap gap-1.5">
                {values.map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => handleParamSelect(key, v)}
                    className={`rounded-full px-3 py-1 text-xs transition-all ${
                      selectedParams[key] === v
                        ? "bg-amber-500 text-white"
                        : "bg-white text-zinc-600 hover:bg-amber-100"
                    }`}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
