"use client";

import { useEffect, useMemo, useRef } from "react";
import { usePresets, type Preset, type LangOption } from "../../hooks/usePresets";
import { cx, SECTION_CLASSES } from "../ui/variants";

type StoryboardGeneratorPanelProps = {
  topic: string;
  setTopic: (value: string) => void;
  description?: string;
  setDescription?: (value: string) => void;
  duration: number;
  setDuration: (value: number) => void;
  language: string;
  setLanguage: (value: string) => void;
  structure: string;
  setStructure: (value: string) => void;
  // External injection (skip internal fetch when provided)
  presets?: Preset[];
  languages?: LangOption[];
  durations?: number[];
};

export default function StoryboardGeneratorPanel({
  topic,
  setTopic,
  description,
  setDescription,
  duration,
  setDuration,
  language,
  setLanguage,
  structure,
  setStructure,
  presets: externalPresets,
  languages: externalLanguages,
  durations: externalDurations,
}: StoryboardGeneratorPanelProps) {
  const hasExternal = !!(externalPresets && externalLanguages && externalDurations);
  const internal = usePresets(hasExternal);
  const presets = externalPresets ?? internal.presets;
  const languages = externalLanguages ?? internal.languages;
  const durations = externalDurations ?? internal.durations;

  // Derive sample topics from presets + structure
  const sampleTopics = useMemo(() => {
    const preset = presets.find((p) => p.structure.toLowerCase() === structure.toLowerCase());
    return preset?.sample_topics ?? [];
  }, [structure, presets]);

  // Update duration when structure changes
  const prevStructureRef = useRef(structure);
  useEffect(() => {
    if (prevStructureRef.current !== structure) {
      prevStructureRef.current = structure;
      const preset = presets.find((p) => p.structure.toLowerCase() === structure.toLowerCase());
      if (preset) {
        setDuration(preset.default_duration);
      }
    }
  }, [structure, presets, setDuration]);

  return (
    <section className={cx(SECTION_CLASSES, "grid gap-6")}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">Story</h2>
          <p className="text-xs text-zinc-500">Topic, structure, and generation settings.</p>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-[1.5fr_1fr]">
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label
              htmlFor="sb-topic"
              className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase"
            >
              Topic
            </label>
            <span
              className={`text-[12px] font-semibold tracking-[0.1em] ${
                topic.length >= 200 ? "text-rose-500" : "text-zinc-400"
              }`}
            >
              {topic.length}/200
            </span>
          </div>
          <textarea
            id="sb-topic"
            data-testid="topic-input"
            value={topic}
            onChange={(e) => setTopic(e.target.value.slice(0, 200))}
            rows={4}
            maxLength={200}
            className="rounded-2xl border border-zinc-200 bg-white/80 p-4 text-sm shadow-inner outline-none focus:border-zinc-400"
            placeholder="예: 혼자 사는 직장인의 하루 루틴, 고양이와 함께하는 일상..."
          />
          {sampleTopics.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-2">
              {sampleTopics.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setTopic(sample)}
                  className="rounded-full border border-zinc-200 bg-zinc-100 px-3 py-1 text-xs text-zinc-600 transition-colors hover:bg-zinc-200 hover:text-zinc-800"
                >
                  {sample}
                </button>
              ))}
            </div>
          )}
          {setDescription !== undefined && (
            <>
              <div className="mt-3 flex items-center justify-between">
                <label
                  htmlFor="sb-description"
                  className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase"
                >
                  Description{" "}
                  <span className="tracking-normal text-zinc-400 normal-case">(optional)</span>
                </label>
                <span
                  className={`text-[12px] font-semibold tracking-[0.1em] ${
                    (description ?? "").length >= 500 ? "text-rose-500" : "text-zinc-400"
                  }`}
                >
                  {(description ?? "").length}/500
                </span>
              </div>
              <textarea
                id="sb-description"
                data-testid="description-input"
                value={description ?? ""}
                onChange={(e) => setDescription(e.target.value.slice(0, 500))}
                rows={3}
                maxLength={500}
                className="rounded-2xl border border-zinc-200 bg-white/80 p-4 text-sm shadow-inner outline-none focus:border-zinc-400"
                placeholder="톤, 대상 독자, 강조 포인트 등을 적어주세요"
              />
            </>
          )}
        </div>
        <div className="grid gap-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-2">
              <label
                htmlFor="sb-duration"
                className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
              >
                Duration
              </label>
              <select
                id="sb-duration"
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              >
                {durations.map((d) => (
                  <option key={d} value={d}>
                    {d}s
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-2">
              <label
                htmlFor="sb-language"
                className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
              >
                Language
              </label>
              <select
                id="sb-language"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              >
                {languages.map((lang) => (
                  <option key={lang.value} value={lang.value}>
                    {lang.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <label
              htmlFor="sb-structure"
              className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
            >
              Structure
            </label>
            <select
              id="sb-structure"
              value={structure}
              onChange={(e) => setStructure(e.target.value)}
              className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
            >
              {presets.map((p) => (
                <option key={p.structure} value={p.structure}>
                  {p.structure}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </section>
  );
}
