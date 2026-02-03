"use client";

import { useEffect, useState } from "react";
import { API_BASE, STRUCTURES } from "../../constants";

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
  selectedCharacterName?: string | null;
  selectedCharacterAvatar?: string | null;
  onGoToSetup?: () => void;
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
  selectedCharacterName,
  selectedCharacterAvatar,
  onGoToSetup,
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
    <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/70 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">Storyboard Generator</h2>
          <p className="text-xs text-zinc-500">
            Generate scene scripts and visual descriptions.
          </p>
        </div>
      </div>
      {/* Character Badge (read-only) */}
      {selectedCharacterName && (
        <button
          type="button"
          onClick={onGoToSetup}
          className="flex items-center gap-2 self-start rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-100 transition-colors"
          title="Setup에서 캐릭터 변경"
        >
          {selectedCharacterAvatar ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={selectedCharacterAvatar}
              alt={selectedCharacterName}
              className="h-5 w-5 rounded-full object-cover"
            />
          ) : (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-200 text-[10px] font-bold text-zinc-500">
              {selectedCharacterName.charAt(0).toUpperCase()}
            </span>
          )}
          <span className="font-medium">{selectedCharacterName}</span>
          <svg className="h-3 w-3 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
          </svg>
        </button>
      )}

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
