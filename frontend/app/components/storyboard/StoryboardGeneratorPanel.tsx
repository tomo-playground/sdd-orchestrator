"use client";

import { useEffect, useState } from "react";
import { API_BASE, STRUCTURES } from "../../constants";
import { cx, SECTION_CLASSES } from "../ui/variants";

type Preset = {
  id: string;
  name: string;
  name_ko: string;
  structure: string;
  sample_topics: string[];
  default_duration: number;
  default_language: string;
};

type StoryboardGeneratorPanelProps = {
  topic: string;
  setTopic: (value: string) => void;
  description: string;
  setDescription: (value: string) => void;
  duration: number;
  setDuration: (value: number) => void;
  language: string;
  setLanguage: (value: string) => void;
  structure: string;
  setStructure: (value: string) => void;
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
}: StoryboardGeneratorPanelProps) {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [sampleTopics, setSampleTopics] = useState<string[]>([]);

  // Fetch presets on mount
  useEffect(() => {
    fetch(`${API_BASE}/presets`)
      .then((res) => res.json())
      .then((data) => {
        const list = data?.presets ?? data;
        if (Array.isArray(list)) {
          setPresets(list);
        }
      })
      .catch(() => setPresets([]));
  }, []);

  // Update sample topics when structure changes
  useEffect(() => {
    const preset = presets.find(
      (p) => p.structure.toLowerCase() === structure.toLowerCase()
    );
    if (preset) {
      setSampleTopics(preset.sample_topics); // eslint-disable-line react-hooks/set-state-in-effect
    } else {
      setSampleTopics([]);  
    }
  }, [structure, presets]);

  return (
    <section className={cx(SECTION_CLASSES, "grid gap-6")}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">Story</h2>
          <p className="text-xs text-zinc-500">
            Topic, structure, and generation settings.
          </p>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-[1.5fr_1fr]">
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Topic
            </label>
            <span className={`text-[10px] font-semibold tracking-[0.1em] ${topic.length >= 200 ? "text-rose-500" : "text-zinc-400"
              }`}>
              {topic.length}/200
            </span>
          </div>
          <textarea
            data-testid="topic-input"
            value={topic}
            onChange={(e) => setTopic(e.target.value.slice(0, 200))}
            rows={4}
            maxLength={200}
            className="rounded-2xl border border-zinc-200 bg-white/80 p-4 text-sm shadow-inner outline-none focus:border-zinc-400"
            placeholder="예: 혼자 사는 직장인의 하루 루틴, 고양이와 함께하는 일상..."
          />
          {sampleTopics.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-1">
              {sampleTopics.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setTopic(sample)}
                  className="px-3 py-1 text-xs rounded-full bg-zinc-100 hover:bg-zinc-200 text-zinc-600 hover:text-zinc-800 transition-colors border border-zinc-200"
                >
                  {sample}
                </button>
              ))}
            </div>
          )}
          <div className="flex items-center justify-between mt-3">
            <label className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Description <span className="text-zinc-400 normal-case tracking-normal">(optional)</span>
            </label>
            <span className={`text-[10px] font-semibold tracking-[0.1em] ${description.length >= 500 ? "text-rose-500" : "text-zinc-400"
              }`}>
              {description.length}/500
            </span>
          </div>
          <textarea
            data-testid="description-input"
            value={description}
            onChange={(e) => setDescription(e.target.value.slice(0, 500))}
            rows={3}
            maxLength={500}
            className="rounded-2xl border border-zinc-200 bg-white/80 p-4 text-sm shadow-inner outline-none focus:border-zinc-400"
            placeholder="톤, 대상 독자, 강조 포인트 등을 적어주세요"
          />
        </div>
        <div className="grid gap-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Duration <span className="text-zinc-400">(10-120s)</span>
              </label>
              <input
                type="number"
                min={10}
                max={120}
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              >
                <option value="Korean">한국어</option>
                <option value="English">English</option>
                <option value="Japanese">日本語</option>
              </select>
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Structure
            </label>
            <select
              value={structure}
              onChange={(e) => setStructure(e.target.value)}
              className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
            >
              {STRUCTURES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </section>
  );
}
