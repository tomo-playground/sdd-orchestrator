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
  SECTION_HEADER_CLASSES,
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

  const { presets, languages, durations, optionalSteps, pipelineMetadata } = usePresets();
  const [disabledSteps, setDisabledSteps] = useState<Set<string>>(new Set());

  // Map optional steps to metadata
  const optionalStepConfigs = pipelineMetadata.filter((m) => optionalSteps.includes(m.key));

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
          onChangeA={(id) => setMonoCharId(id)}
          onChangeB={(id) => setSpeakerBId(id)}
        />
      </div>

      {/* Divider + Agent Settings */}
      <div className="mt-5 space-y-4 border-t border-zinc-200/60 pt-5">
        <h3 className={SECTION_HEADER_CLASSES}>Agent Settings</h3>

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
        {optionalStepConfigs.length > 0 && (
          <div>
            <label className={LABEL}>Pipeline Steps</label>
            <div className="space-y-2">
              {optionalStepConfigs.map((step) => (
                <label
                  key={step.key}
                  className="flex cursor-pointer items-start gap-2 text-xs text-zinc-600 group"
                >
                  <input
                    type="checkbox"
                    checked={!disabledSteps.has(step.key)}
                    onChange={() => toggleStep(step.key)}
                    className="mt-0.5 h-3.5 w-3.5 rounded border-zinc-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  <div className="flex flex-col">
                    <span className="font-medium group-hover:text-zinc-900 transition-colors">
                      {step.label}
                      <span className="ml-1.5 text-[11px] text-zinc-400 font-normal">(optional)</span>
                    </span>
                    <span className="text-[11px] text-zinc-400 leading-tight">{step.desc}</span>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Source Materials & References */}
        <div>
          <label className={LABEL}>Source Materials & References</label>
          <textarea
            value={references}
            onChange={(e) => setReferences(e.target.value)}
            rows={3}
            placeholder={
              "https://example.com/article\nhttps://youtube.com/watch?v=...\n참고할 텍스트 메모 (URL이 아닌 줄은 텍스트 레퍼런스로 사용)"
            }
            className={FORM_TEXTAREA_CLASSES}
          />
          {(() => {
            const lines = references.split("\n").filter((l) => l.trim());
            const urlCount = lines.filter((l) => /^https?:\/\//i.test(l.trim())).length;
            const textCount = lines.length - urlCount;
            if (lines.length === 0) return null;
            return (
              <div className="mt-1.5 flex gap-2">
                {urlCount > 0 && (
                  <span className="rounded bg-blue-50 px-2 py-0.5 text-[12px] font-medium text-blue-600">
                    URL {urlCount}개 — 자동 수집 & AI 분석
                  </span>
                )}
                {textCount > 0 && (
                  <span className="rounded bg-zinc-100 px-2 py-0.5 text-[12px] font-medium text-zinc-500">
                    텍스트 {textCount}개 — 레퍼런스 가이드
                  </span>
                )}
              </div>
            );
          })()}
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
