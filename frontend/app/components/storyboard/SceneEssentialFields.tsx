"use client";

import { useEffect, useState } from "react";
import type { Scene } from "../../types";
import { isMultiCharStructure } from "../../utils/structure";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { Input, Textarea } from "../ui";
import { API_BASE } from "../../constants";
import type { ReadingSpeedConfig } from "../../hooks/usePresets";

type SceneEssentialFieldsProps = {
  scene: Scene;
  structure?: string;
  onUpdateScene: (updates: Partial<Scene>) => void;
  onSpeakerChange: (speaker: Scene["speaker"]) => void;
  onImageUpload: (file: File | undefined) => void;
};

export default function SceneEssentialFields({
  scene,
  structure,
  onUpdateScene,
  onSpeakerChange,
  onImageUpload,
}: SceneEssentialFieldsProps) {
  const hasMultipleSpeakers = isMultiCharStructure(structure ?? "");
  const isNarratedDialogue = structure?.toLowerCase() === "narrated dialogue";

  return (
    <>
      {/* Script */}
      <div className="grid gap-2">
        <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Script
        </label>
        <Textarea
          value={scene.script}
          onChange={(e) => onUpdateScene({ script: e.target.value })}
          rows={3}
          className="text-sm"
        />
        <ScriptMeta script={scene.script} />
      </div>

      {/* Speaker, Duration, Upload - 3 Column Grid */}
      <div className="grid grid-cols-3 gap-3">
        <div className="flex flex-col gap-2">
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Speaker
          </label>
          <select
            value={scene.speaker}
            onChange={(e) => onSpeakerChange(e.target.value as Scene["speaker"])}
            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
          >
            {isNarratedDialogue && <option value="Narrator">Narrator</option>}
            <option value="A">Actor A</option>
            {hasMultipleSpeakers && <option value="B">Actor B</option>}
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Duration
          </label>
          <Input
            type="number"
            min={1}
            max={10}
            value={scene.duration}
            onChange={(e) => {
              const num = Number(e.target.value);
              if (Number.isNaN(num)) return;
              onUpdateScene({ duration: Math.min(10, Math.max(1, Math.round(num))) });
            }}
            onBlur={(e) => {
              if (!e.target.value.trim()) onUpdateScene({ duration: 3 });
            }}
            className="text-sm"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Image
          </label>
          <label className="flex h-10 cursor-pointer items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white/80 text-[12px] font-semibold tracking-[0.2em] text-zinc-600 uppercase hover:bg-zinc-50">
            Upload
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => onImageUpload(e.target.files?.[0])}
            />
          </label>
        </div>
      </div>
    </>
  );
}

/* ---- Script Meta (character count + reading time) ---- */

// Module-level cache for reading speed from /presets API (fetched once)
let _cachedReadingSpeed: Record<string, ReadingSpeedConfig> | null = null;
let _fetchPromise: Promise<void> | null = null;

function useReadingSpeed(): Record<string, ReadingSpeedConfig> {
  const [speed, setSpeed] = useState<Record<string, ReadingSpeedConfig>>(_cachedReadingSpeed ?? {});

  useEffect(() => {
    if (_cachedReadingSpeed) {
      setSpeed(_cachedReadingSpeed);
      return;
    }
    if (!_fetchPromise) {
      _fetchPromise = fetch(`${API_BASE}/presets`)
        .then((res) => res.json())
        .then((data) => {
          if (data?.reading_speed) {
            _cachedReadingSpeed = data.reading_speed;
          }
        })
        .catch(() => {});
    }
    _fetchPromise.then(() => {
      if (_cachedReadingSpeed) setSpeed(_cachedReadingSpeed);
    });
  }, []);

  return speed;
}

function ScriptMeta({ script }: { script: string }) {
  const language = useStoryboardStore((s) => s.language);
  const readingSpeed = useReadingSpeed();
  const text = script.trim();
  if (!text) return null;

  const cfg = readingSpeed[language];
  const charCount = text.replace(/\s/g, "").length;
  const wordCount = text.split(/\s+/).length;
  const isWordBased = cfg?.unit === "words";
  const count = isWordBased ? wordCount : charCount;
  const rate = isWordBased ? (cfg?.wps ?? 2.5) : (cfg?.cps ?? 4);
  const readTime = count / rate;
  const unit = isWordBased ? "words" : language === "Japanese" ? "字" : "자";

  return (
    <div className="flex items-center gap-2 text-[11px] text-zinc-400">
      <span>
        {count}
        {unit}
      </span>
      <span>·</span>
      <span>읽기 {readTime.toFixed(1)}초</span>
    </div>
  );
}
