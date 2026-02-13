"use client";

import type { Scene, Background } from "../../types";
import { isMultiCharStructure } from "../../utils/structure";
import { useStoryboardStore } from "../../store/useStoryboardStore";

type SceneScriptFieldsProps = {
  scene: Scene;
  structure?: string;
  onUpdateScene: (updates: Partial<Scene>) => void;
  onSpeakerChange: (speaker: Scene["speaker"]) => void;
  onImageUpload: (file: File | undefined) => void;
  backgrounds?: Background[];
};

export default function SceneScriptFields({
  scene,
  structure,
  onUpdateScene,
  onSpeakerChange,
  onImageUpload,
  backgrounds = [],
}: SceneScriptFieldsProps) {
  const hasMultipleSpeakers = isMultiCharStructure(structure ?? "");
  const isNarratedDialogue = structure?.toLowerCase() === "narrated dialogue";
  const selectedBackground = backgrounds.find((bg) => bg.id === scene.background_id);

  return (
    <>
      {/* Script */}
      <div className="grid gap-2">
        <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Script
        </label>
        <textarea
          value={scene.script}
          onChange={(e) => onUpdateScene({ script: e.target.value })}
          rows={3}
          className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
        />
        <ScriptMeta script={scene.script} />
      </div>

      {/* Speaker, Duration, Upload */}
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
          <input
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
            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
          />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Image
          </label>
          <label className="flex h-10 cursor-pointer items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white/80 text-[12px] font-semibold tracking-[0.2em] text-zinc-600 uppercase">
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

      {/* Background Picker */}
      {backgrounds.length > 0 && (
        <div className="grid gap-2">
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Background
          </label>
          <select
            value={scene.background_id ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              onUpdateScene({ background_id: val ? Number(val) : null });
            }}
            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
          >
            <option value="">None</option>
            {backgrounds.map((bg) => (
              <option key={bg.id} value={bg.id}>
                {bg.name}
                {bg.category ? ` (${bg.category})` : ""}
              </option>
            ))}
          </select>
          {selectedBackground?.tags && selectedBackground.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {selectedBackground.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}

/* ---- Script Meta (character count + reading time) ---- */

type LangConfig = { cps: number; min: number; max: number; unit: string };

const LANG_CONFIG: Record<string, LangConfig> = {
  Korean: { cps: 4, min: 15, max: 30, unit: "자" },
  Japanese: { cps: 5, min: 12, max: 25, unit: "字" },
  English: { cps: 2.5, min: 8, max: 15, unit: "words" },
};
const DEFAULT_CPS = 2.5;

function ScriptMeta({ script }: { script: string }) {
  const language = useStoryboardStore((s) => s.language);
  const text = script.trim();
  if (!text) return null;

  const cfg = LANG_CONFIG[language];
  const charCount = text.replace(/\s/g, "").length;
  const wordCount = text.split(/\s+/).length;
  const count = cfg ? charCount : wordCount;
  const readTime = cfg ? charCount / cfg.cps : wordCount / DEFAULT_CPS;
  const unit = cfg?.unit ?? "words";
  const range = cfg ? { min: cfg.min, max: cfg.max } : null;

  const isOver = range != null && count > range.max;
  const isUnder = range != null && count < range.min;

  return (
    <div className="flex items-center gap-2 text-[11px] text-zinc-400">
      <span>
        {count}
        {unit}
      </span>
      <span>·</span>
      <span>읽기 {readTime.toFixed(1)}초</span>
      {(isOver || isUnder) && range && (
        <>
          <span>·</span>
          <span className="rounded-full bg-amber-50 px-1.5 py-0.5 text-[11px] font-medium text-amber-600">
            {isOver ? "권장 초과" : "권장 미만"} ({range.min}~{range.max}
            {unit})
          </span>
        </>
      )}
    </div>
  );
}
