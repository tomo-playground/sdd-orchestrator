"use client";

import { useState } from "react";
import { Loader2, Sparkles, ChevronRight, ChevronDown } from "lucide-react";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import CharacterSelectSection from "./CharacterSelectSection";
import PipelineStepper from "./PipelineStepper";
import Button from "../ui/Button";
import { SECTION_CLASSES, FORM_TEXTAREA_CLASSES } from "../ui/variants";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import type { ScriptEditorActions } from "../../hooks/useScriptEditor";
import type { Preset, LangOption } from "../../hooks/usePresets";

type Props = {
  editor: ScriptEditorActions;
  presets: Preset[];
  languages: LangOption[];
  durations: number[];
  onGenerate: () => void;
  expandedStep: string | null;
  onStepClick: (id: string) => void;
};

function ReferencesToggle({ editor }: { editor: ScriptEditorActions }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-8 border-t border-zinc-200/60 pt-5">
      <h3 className="mb-4 text-sm font-semibold text-zinc-800">Advanced Settings</h3>
      <div>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="group flex w-full items-center gap-1.5 text-left text-sm font-medium text-zinc-700 hover:text-zinc-900"
        >
          {open ? (
            <ChevronDown className="h-4 w-4 text-zinc-400 group-hover:text-zinc-600" />
          ) : (
            <ChevronRight className="h-4 w-4 text-zinc-400 group-hover:text-zinc-600" />
          )}
          References <span className="font-normal text-zinc-400 normal-case">(optional)</span>
        </button>
        {open && (
          <div className="mt-3 space-y-2">
            <textarea
              value={editor.references}
              onChange={(e) => editor.setField("references", e.target.value)}
              rows={3}
              maxLength={2000}
              className={FORM_TEXTAREA_CLASSES}
              placeholder={
                "참고 URL 또는 소재 텍스트를 입력하세요\nhttps://example.com/article\n또는 직접 소재 텍스트를 입력..."
              }
            />
            <p className="text-[11px] text-zinc-400">
              줄바꿈으로 구분 (URL + 텍스트 혼합 가능, 최대 5개)
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ScriptOptionsCard({
  editor,
  presets,
  languages,
  durations,
  onGenerate,
  expandedStep,
  onStepClick,
}: Props) {
  const casting = useStoryboardStore((s) => s.castingRecommendation);
  return (
    <section className={SECTION_CLASSES}>
      {/* Header */}
      <div className="mb-8 flex items-center justify-between border-b border-zinc-100 pb-5">
        <div>
          <h2 className="text-lg font-bold text-zinc-900">Script Options</h2>
          <p className="mt-1 text-sm text-zinc-500">
            Configure your video length, topic, and generation style.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {editor.scenes.length > 0 && (
            <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-600">
              {editor.scenes.length} scenes
            </span>
          )}
        </div>
      </div>

      <StoryboardGeneratorPanel
        embedded
        presets={presets}
        languages={languages}
        durations={durations}
        recommendedStructure={casting?.structure ?? undefined}
        topic={editor.topic}
        setTopic={(v) => editor.setField("topic", v)}
        description={editor.description}
        setDescription={(v) => editor.setField("description", v)}
        duration={editor.duration}
        setDuration={(v) => editor.setField("duration", v)}
        language={editor.language}
        setLanguage={(v) => editor.setField("language", v)}
        structure={editor.structure}
        setStructure={(v) => editor.setField("structure", v)}
      />

      {/* Divider + Characters */}
      <div className="mt-8 border-t border-zinc-200/60 pt-5">
        <CharacterSelectSection
          embedded
          structure={editor.structure}
          characterId={editor.characterId}
          characterBId={editor.characterBId}
          onChangeA={(id, name) => {
            editor.setField("characterId", id);
            editor.setField("characterName", name);
          }}
          onChangeB={(id, name) => {
            editor.setField("characterBId", id);
            editor.setField("characterBName", name);
          }}
        />
      </div>

      {/* References — always visible */}
      <ReferencesToggle editor={editor} />

      {/* Generate button — card footer */}
      <div className="mt-8 border-t border-zinc-200/60 pt-6">
        <div className="flex justify-end">
          <Button
            size="md"
            variant="primary"
            disabled={!editor.topic.trim() || editor.isGenerating}
            onClick={onGenerate}
          >
            {editor.isGenerating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {editor.isGenerating ? editor.progress?.label || "Generating..." : "Generate Script"}
          </Button>
        </div>
      </div>

      {/* Pipeline stepper */}
      {editor.pipelineSteps.length > 0 && (
        <PipelineStepper
          steps={editor.pipelineSteps}
          currentNode={editor.progress?.node}
          percent={editor.progress?.percent}
          onStepClick={onStepClick}
        />
      )}
    </section>
  );
}
