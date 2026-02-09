"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { API_BASE } from "../../constants";
import type { ShortsSessionCreate } from "../../types/creative";
import CharacterPicker from "./CharacterPicker";

type LangOption = { value: string; label: string };
type PresetOption = { structure: string; name: string };

type Props = {
  loading: boolean;
  onSubmit: (data: ShortsSessionCreate) => void;
};

const LABEL = "mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase";
const INPUT =
  "w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none";

export default function ShortsSetupForm({ loading, onSubmit }: Props) {
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState<number>(30);
  const [structure, setStructure] = useState<string>("Monologue");
  const [language, setLanguage] = useState<string>("Korean");
  const [directorMode, setDirectorMode] = useState<string>("advisor");
  const [maxRounds, setMaxRounds] = useState<number>(2);
  const [references, setReferences] = useState("");
  const [characterIds, setCharacterIds] = useState<Record<string, number>>({});

  const [structures, setStructures] = useState<PresetOption[]>([
    { structure: "Monologue", name: "Monologue" },
    { structure: "Dialogue", name: "Dialogue" },
    { structure: "Narrated Dialogue", name: "Narrated Dialogue" },
  ]);
  const [languages, setLanguages] = useState<LangOption[]>([
    { value: "Korean", label: "Korean" },
    { value: "English", label: "English" },
    { value: "Japanese", label: "Japanese" },
  ]);
  const [durations, setDurations] = useState<number[]>([15, 30, 45, 60]);

  useEffect(() => {
    fetch(`${API_BASE}/presets`)
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data?.presets)) {
          setStructures(data.presets.map((p: PresetOption) => ({ structure: p.structure, name: p.name })));
        }
        if (Array.isArray(data?.languages)) setLanguages(data.languages);
        if (Array.isArray(data?.durations)) setDurations(data.durations);
      })
      .catch(() => {});
  }, []);

  const isMultiChar = structure === "Dialogue" || structure === "Narrated Dialogue";
  const handleCharacterChange = useCallback((ids: Record<string, number>) => setCharacterIds(ids), []);

  const handleSubmit = () => {
    if (!topic.trim()) return;
    const refs = references
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);

    onSubmit({
      topic: topic.trim(),
      duration,
      structure,
      language,
      character_ids: isMultiChar && Object.keys(characterIds).length > 0 ? characterIds : undefined,
      director_mode: directorMode,
      max_rounds: maxRounds,
      references: refs.length > 0 ? refs : undefined,
    });
  };

  return (
    <div className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5">
      <div className="rounded-lg bg-gradient-to-r from-emerald-500 to-green-400 px-4 py-2.5">
        <p className="text-[10px] font-bold tracking-wider text-white/70 uppercase">
          Shorts Pipeline
        </p>
        <p className="text-xs font-semibold text-white">Create a short-form video from a topic</p>
      </div>

      {/* Topic */}
      <div>
        <label className={LABEL}>Topic</label>
        <textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          rows={3}
          placeholder="Describe your shorts topic..."
          className={INPUT}
        />
      </div>

      {/* Duration + Structure */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={LABEL}>Duration</label>
          <select
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            className={INPUT}
          >
            {durations.map((d) => (
              <option key={d} value={d}>
                {d}s
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={LABEL}>Structure</label>
          <select
            value={structure}
            onChange={(e) => setStructure(e.target.value)}
            className={INPUT}
          >
            {structures.map((s) => (
              <option key={s.structure} value={s.structure}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Language + Director Mode */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={LABEL}>Language</label>
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className={INPUT}>
            {languages.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={LABEL}>Director Mode</label>
          <select
            value={directorMode}
            onChange={(e) => setDirectorMode(e.target.value)}
            className={INPUT}
          >
            <option value="advisor">advisor — Always ask for your choice</option>
            <option value="auto">auto — Auto-select when score gap &gt; 0.15</option>
          </select>
        </div>
      </div>

      {/* Character Pickers (for Dialogue / Narrated Dialogue) */}
      {isMultiChar && (
        <CharacterPicker
          structure={structure}
          inputClass={INPUT}
          labelClass={LABEL}
          onChange={handleCharacterChange}
        />
      )}

      {/* References (optional) */}
      <div>
        <label className={LABEL}>References (optional)</label>
        <textarea
          value={references}
          onChange={(e) => setReferences(e.target.value)}
          rows={2}
          placeholder="Paste URLs or text references, one per line..."
          className={INPUT}
        />
        <p className="mt-0.5 text-[10px] text-zinc-400">
          Reference analyst will extract patterns for concept generation
        </p>
      </div>

      {/* Max Rounds + Submit */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <label className={LABEL}>Max Rounds</label>
          <input
            type="number"
            min={1}
            max={5}
            value={maxRounds}
            onChange={(e) => setMaxRounds(Number(e.target.value))}
            className="w-16 rounded-lg border border-zinc-200 bg-zinc-50 px-2 py-1.5 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={loading || !topic.trim()}
          className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-zinc-300"
        >
          {loading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          Start Pipeline
        </button>
      </div>
    </div>
  );
}
