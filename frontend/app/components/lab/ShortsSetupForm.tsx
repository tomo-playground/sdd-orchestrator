"use client";

import { useState } from "react";
import { Loader2, Play } from "lucide-react";
import type { ShortsSessionCreate } from "../../types/creative";
import { usePresets } from "../../hooks/usePresets";
import { isMultiCharStructure } from "../../utils/structure";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import CharacterSelectSection from "../scripts/CharacterSelectSection";
import Button from "../ui/Button";
import {
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
  const [monoCharId, setMonoCharId] = useState<number | null>(null);
  const [speakerBId, setSpeakerBId] = useState<number | null>(null);

  const { presets, languages, durations, optionalSteps } = usePresets();
  const [disabledSteps, setDisabledSteps] = useState<Set<string>>(new Set());

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
    const lines = references
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);

    // Auto-classify: URLs vs text references
    const urls = lines.filter((l) => /^https?:\/\//i.test(l));
    const textRefs = lines.filter((l) => !/^https?:\/\//i.test(l));

    const multiChar = isMultiCharStructure(structure);
    const charIds: Record<string, number> = {};
    if (multiChar) {
      if (monoCharId !== null) charIds["A"] = monoCharId;
      if (speakerBId !== null) charIds["B"] = speakerBId;
    }

    onSubmit({
      topic: topic.trim(),
      description: description.trim() || undefined,
      duration,
      structure,
      language,
      character_id: !multiChar && monoCharId ? monoCharId : undefined,
      character_ids: multiChar && Object.keys(charIds).length > 0 ? charIds : undefined,
      director_mode: directorMode,
      max_rounds: maxRounds,
      references: textRefs.length > 0 ? textRefs : undefined,
      material_urls: urls.length > 0 ? urls : undefined,
      disabled_steps: disabledSteps.size > 0 ? Array.from(disabledSteps) : undefined,
    });
  };

  return (
    <section className={SECTION_CLASSES}>
      {/* Story (embedded — no card wrapper, no section header) */}
      <StoryboardGeneratorPanel
        embedded
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

      {/* Divider + Characters */}
      <div className="mt-6 border-t border-zinc-200/60 pt-5">
        <CharacterSelectSection
          embedded
          structure={structure}
          characterId={monoCharId}
          characterBId={speakerBId}
          onChangeA={setMonoCharId}
          onChangeB={setSpeakerBId}
        />
      </div>

      {/* Divider + Agent Settings */}
      <div className="mt-5 space-y-4 border-t border-zinc-200/60 pt-5">
        <h3 className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Agent Settings
        </h3>

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
            URLs are auto-fetched and analyzed. Text lines are used as reference guidelines.
          </p>
        </div>

        {/* Max Rounds */}
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
      </div>

      {/* Submit footer */}
      <div className="mt-5 flex justify-end border-t border-zinc-200/60 pt-5">
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
  );
}
