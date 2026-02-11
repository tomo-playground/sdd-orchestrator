"use client";

import { useCallback, useState } from "react";
import { Loader2, Play } from "lucide-react";
import type { ShortsSessionCreate } from "../../types/creative";
import { usePresets } from "../../hooks/usePresets";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import CharacterSelectSection from "../scripts/CharacterSelectSection";
import Button from "../ui/Button";
import {
  cx,
  SECTION_CLASSES,
  FORM_INPUT_CLASSES,
  FORM_TEXTAREA_CLASSES,
  FORM_LABEL_CLASSES,
} from "../ui/variants";

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
  const [description, setDescription] = useState("");
  const [duration, setDuration] = useState<number>(initialValues?.duration ?? 30);
  const [structure, setStructure] = useState<string>(initialValues?.structure ?? "Monologue");
  const [language, setLanguage] = useState<string>(initialValues?.language ?? "Korean");
  const [directorMode, setDirectorMode] = useState<string>("advisor");
  const [maxRounds, setMaxRounds] = useState<number>(2);
  const [references, setReferences] = useState("");
  const [characterIds, setCharacterIds] = useState<Record<string, number>>({});
  const [monoCharId, setMonoCharId] = useState<number | null>(null);
  const [speakerBId, setSpeakerBId] = useState<number | null>(null);

  const { presets, languages, durations, optionalSteps } = usePresets();
  const [disabledSteps, setDisabledSteps] = useState<Set<string>>(new Set());

  const isMultiChar = structure === "Dialogue" || structure === "Narrated Dialogue";

  const handleCharAChange = useCallback((id: number | null) => {
    setMonoCharId(id);
    setCharacterIds((prev) => {
      const next = { ...prev };
      if (id !== null) next["A"] = id;
      else delete next["A"];
      return next;
    });
  }, []);

  const handleCharBChange = useCallback((id: number | null) => {
    setSpeakerBId(id);
    setCharacterIds((prev) => {
      const next = { ...prev };
      if (id !== null) next["B"] = id;
      else delete next["B"];
      return next;
    });
  }, []);

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
      description: description.trim() || undefined,
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
    <div className="space-y-6">
      {/* Shared section: Topic, Description, Sample Topics, Duration, Language, Structure */}
      <StoryboardGeneratorPanel
        presets={presets}
        languages={languages}
        durations={durations}
        topic={topic}
        setTopic={setTopic}
        description={description}
        setDescription={setDescription}
        duration={duration}
        setDuration={setDuration}
        language={language}
        setLanguage={setLanguage}
        structure={structure}
        setStructure={setStructure}
      />

      {/* Character selection */}
      <CharacterSelectSection
        structure={structure}
        characterId={monoCharId}
        characterBId={speakerBId}
        onChangeA={handleCharAChange}
        onChangeB={handleCharBChange}
      />

      {/* Agent-specific settings */}
      <section className={cx(SECTION_CLASSES, "space-y-4")}>
        <div>
          <h3 className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Agent Settings
          </h3>
        </div>

        {/* Director Mode */}
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
      </section>
    </div>
  );
}
