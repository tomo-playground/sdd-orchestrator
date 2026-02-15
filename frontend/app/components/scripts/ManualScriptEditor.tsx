"use client";

import { Loader2, Sparkles } from "lucide-react";
import { usePresets } from "../../hooks/usePresets";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import CharacterSelectSection from "./CharacterSelectSection";
import ReviewApprovalPanel from "./ReviewApprovalPanel";
import ScriptFeedbackWidget from "./ScriptFeedbackWidget";
import Button from "../ui/Button";
import { SECTION_CLASSES } from "../ui/variants";
import type { ScriptEditorActions } from "../../hooks/useScriptEditor";

type Props = {
  editor: ScriptEditorActions;
};

export default function ManualScriptEditor({ editor }: Props) {
  const { presets, languages, durations } = usePresets();
  const { confirm, dialogProps } = useConfirm();

  return (
    <div className="space-y-6">
      {/* Story settings + Characters + Generate — single card */}
      <section className={SECTION_CLASSES}>
        <StoryboardGeneratorPanel
          embedded
          presets={presets}
          languages={languages}
          durations={durations}
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
        <div className="mt-6 border-t border-zinc-200/60 pt-5">
          <CharacterSelectSection
            embedded
            structure={editor.structure}
            characterId={editor.characterId}
            characterBId={editor.characterBId}
            onChangeA={(id) => editor.setField("characterId", id)}
            onChangeB={(id) => editor.setField("characterBId", id)}
          />
        </div>

        {/* Preset selector — Full mode only */}
        {editor.mode === "full" && (
          <div className="mt-4 border-t border-zinc-200/60 pt-4">
            <label className="mb-1 block text-xs font-medium text-zinc-500">Preset</label>
            <select
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-800"
              value={editor.preset ?? "full_auto"}
              onChange={(e) => editor.setField("preset", e.target.value)}
            >
              <option value="full_auto">풀 오토 -- AI 자동 생성 후 승인</option>
              <option value="creator">크리에이터 -- AI 초안 + 사용자 결정</option>
            </select>
          </div>
        )}

        {/* Generate button — card footer */}
        <div className="mt-5 flex justify-end border-t border-zinc-200/60 pt-5">
          <Button
            size="md"
            variant="gradient"
            disabled={!editor.topic.trim() || editor.isGenerating}
            onClick={async () => {
              if (editor.scenes.length > 0) {
                const ok = await confirm({
                  title: "스크립트 재생성",
                  message: `기존 ${editor.scenes.length}개 씬이 교체됩니다. 계속하시겠습니까?`,
                  confirmLabel: "재생성",
                  variant: "danger",
                });
                if (!ok) return;
              }
              editor.generate();
            }}
          >
            {editor.isGenerating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {editor.isGenerating ? editor.progress?.label || "Generating..." : "Generate Script"}
          </Button>
        </div>

        {/* Progress bar */}
        {editor.progress && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between text-xs text-zinc-500">
              <span>{editor.progress.label}</span>
              <span>{editor.progress.percent}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100">
              <div
                className="h-full rounded-full bg-zinc-900 transition-all duration-500"
                style={{ width: `${editor.progress.percent}%` }}
              />
            </div>
          </div>
        )}
      </section>

      {/* Review approval panel — shown when waiting for user input */}
      {editor.isWaitingForInput && (
        <ReviewApprovalPanel
          scenes={editor.scenes}
          onApprove={() => editor.resume("approve")}
          onRevise={(feedback) => editor.resume("revise", feedback)}
        />
      )}

      {/* Feedback widget — shown after generation completes */}
      {editor.scenes.length > 0 && !editor.isGenerating && !editor.feedbackSubmitted && (
        <ScriptFeedbackWidget onSubmit={editor.submitFeedback} />
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
