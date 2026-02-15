"use client";

import type { Scene } from "../../types";
import { isMultiCharStructure } from "../../utils/structure";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { Input, Textarea } from "../ui";

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
