"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { API_BASE } from "../../constants";
import type { ShortsSessionCreate } from "../../types/creative";
import CharacterPicker from "./CharacterPicker";
import Button from "../ui/Button";
import {
  cx,
  SECTION_CLASSES,
  FORM_INPUT_CLASSES,
  FORM_TEXTAREA_CLASSES,
  FORM_LABEL_CLASSES,
} from "../ui/variants";

type CharacterOption = { id: number; name: string };

type LangOption = { value: string; label: string };
type PresetOption = { structure: string; name: string };

type Props = {
  loading: boolean;
  onSubmit: (data: ShortsSessionCreate) => void;
  initialValues?: Partial<{
    topic: string;
    duration: number;
    structure: string;
    language: string;
  }>;
};

const LABEL = `mb-1 block ${FORM_LABEL_CLASSES}`;
const INPUT = FORM_INPUT_CLASSES;

export default function ShortsSetupForm({ loading, onSubmit, initialValues }: Props) {
  const [topic, setTopic] = useState(initialValues?.topic ?? "");
  const [duration, setDuration] = useState<number>(initialValues?.duration ?? 30);
  const [structure, setStructure] = useState<string>(initialValues?.structure ?? "Monologue");
  const [language, setLanguage] = useState<string>(initialValues?.language ?? "Korean");
  const [directorMode, setDirectorMode] = useState<string>("advisor");
  const [maxRounds, setMaxRounds] = useState<number>(2);
  const [references, setReferences] = useState("");
  const [characterIds, setCharacterIds] = useState<Record<string, number>>({});
  const [monoCharId, setMonoCharId] = useState<number | null>(null);
  const [characters, setCharacters] = useState<CharacterOption[]>([]);

  const [optionalSteps, setOptionalSteps] = useState<string[]>([]);
  const [disabledSteps, setDisabledSteps] = useState<Set<string>>(new Set());

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
          setStructures(
            data.presets.map((p: PresetOption) => ({ structure: p.structure, name: p.name }))
          );
        }
        if (Array.isArray(data?.languages)) setLanguages(data.languages);
        if (Array.isArray(data?.durations)) setDurations(data.durations);
        if (Array.isArray(data?.optional_steps)) setOptionalSteps(data.optional_steps);
      })
      .catch(() => {});
    fetch(`${API_BASE}/characters`)
      .then((res) => res.json())
      .then((data) => setCharacters(data.items ?? data))
      .catch(() => {});
  }, []);

  const isMultiChar = structure === "Dialogue" || structure === "Narrated Dialogue";
  const handleCharacterChange = useCallback(
    (ids: Record<string, number>) => setCharacterIds(ids),
    []
  );

  const toggleStep = (step: string) => {
    setDisabledSteps((prev) => {
      const next = new Set(prev);
      if (next.has(step)) next.delete(step);
      else next.add(step);
      return next;
    });
  };

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
      character_id: !isMultiChar && monoCharId ? monoCharId : undefined,
      character_ids: isMultiChar && Object.keys(characterIds).length > 0 ? characterIds : undefined,
      director_mode: directorMode,
      max_rounds: maxRounds,
      references: refs.length > 0 ? refs : undefined,
      disabled_steps: disabledSteps.size > 0 ? Array.from(disabledSteps) : undefined,
    });
  };

  return (
    <div className={cx(SECTION_CLASSES, "space-y-4")}>
      <div>
        <h2 className="text-lg font-semibold text-zinc-900">Story</h2>
        <p className="text-xs text-zinc-500">
          AI agents create an optimized script through debate and pipeline.
        </p>
      </div>

      {/* Topic */}
      <div>
        <label className={LABEL}>Topic</label>
        <textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          rows={4}
          maxLength={200}
          placeholder="예: 혼자 사는 직장인의 하루 루틴, 고양이와 함께하는 일상..."
          className={FORM_TEXTAREA_CLASSES}
        />
        <span
          className={`text-[12px] font-semibold tracking-[0.1em] ${topic.length >= 200 ? "text-rose-500" : "text-zinc-400"}`}
        >
          {topic.length}/200
        </span>
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

      {/* Pipeline Steps (optional) */}
      {optionalSteps.length > 0 && (
        <div>
          <label className={LABEL}>Pipeline Steps</label>
          <div className="space-y-1.5">
            {optionalSteps.map((step) => (
              <label
                key={step}
                className="flex cursor-pointer items-center gap-2 text-xs text-zinc-600"
              >
                <input
                  type="checkbox"
                  checked={!disabledSteps.has(step)}
                  onChange={() => toggleStep(step)}
                  className="h-3.5 w-3.5 rounded border-zinc-300 text-emerald-600 focus:ring-emerald-500"
                />
                {step.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                <span className="text-[12px] text-zinc-400">(optional)</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Character Selection */}
      {isMultiChar ? (
        <CharacterPicker
          structure={structure}
          inputClass={INPUT}
          labelClass={LABEL}
          onChange={handleCharacterChange}
        />
      ) : (
        characters.length > 0 && (
          <div>
            <label className={LABEL}>Character (optional)</label>
            <select
              value={monoCharId ?? ""}
              onChange={(e) => setMonoCharId(e.target.value ? Number(e.target.value) : null)}
              className={INPUT}
            >
              <option value="">None</option>
              {characters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        )
      )}

      {/* References (optional) */}
      <div>
        <label className={LABEL}>References (optional)</label>
        <textarea
          value={references}
          onChange={(e) => setReferences(e.target.value)}
          rows={2}
          placeholder="Paste URLs or text references, one per line..."
          className={FORM_TEXTAREA_CLASSES}
        />
        <p className="mt-0.5 text-[12px] text-zinc-400">
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
            className="w-16 rounded-2xl border border-zinc-200 bg-white/80 px-2 py-1.5 text-sm outline-none focus:border-zinc-400"
          />
        </div>
        <Button
          size="md"
          variant="success"
          disabled={loading || !topic.trim()}
          onClick={handleSubmit}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {loading ? "Starting..." : "Start Pipeline"}
        </Button>
      </div>
    </div>
  );
}
