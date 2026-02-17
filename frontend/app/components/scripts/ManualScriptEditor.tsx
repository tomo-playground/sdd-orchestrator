"use client";

import { useState } from "react";
import { Loader2, Sparkles, Play, PenLine } from "lucide-react";
import { usePresets } from "../../hooks/usePresets";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";
import StoryboardGeneratorPanel from "../storyboard/StoryboardGeneratorPanel";
import CharacterSelectSection from "./CharacterSelectSection";
import ConceptSelectionPanel from "./ConceptSelectionPanel";
import ReviewApprovalPanel from "./ReviewApprovalPanel";
import PipelineStepper from "./PipelineStepper";
import AgentReasoningPanel from "./AgentReasoningPanel";
import ScriptFeedbackWidget from "./ScriptFeedbackWidget";
import Button from "../ui/Button";
import { SECTION_CLASSES, FORM_TEXTAREA_CLASSES } from "../ui/variants";
import { useUIStore } from "../../store/useUIStore";
import { persistStoryboard } from "../../store/actions/storyboardActions";
import type { ScriptEditorActions } from "../../hooks/useScriptEditor";

type Props = {
  editor: ScriptEditorActions;
};

export default function ManualScriptEditor({ editor }: Props) {
  const { presets, languages, durations } = usePresets();
  const { confirm, dialogProps } = useConfirm();
  const [isStarting, setIsStarting] = useState(false);
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  const handleStartProduction = async () => {
    setIsStarting(true);
    try {
      const saved = await persistStoryboard();
      if (saved) {
        useUIStore.getState().setPendingAutoRun(true);
      } else {
        useUIStore.getState().showToast("저장에 실패했습니다. 다시 시도해주세요.", "error");
      }
    } finally {
      setIsStarting(false);
    }
  };

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

        {/* References — Full mode only */}
        {editor.mode === "full" && (
          <details className="mt-4 border-t border-zinc-200/60 pt-4">
            <summary className="cursor-pointer text-xs font-medium text-zinc-500">
              References <span className="text-zinc-400">(optional)</span>
            </summary>
            <div className="mt-2 space-y-2">
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
          </details>
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

        {/* Pipeline stepper */}
        {editor.pipelineSteps.length > 0 && (
          <PipelineStepper
            steps={editor.pipelineSteps}
            currentNode={editor.progress?.node}
            percent={editor.progress?.percent}
            onStepClick={(id) => setExpandedStep((prev) => (prev === id ? null : id))}
          />
        )}
      </section>

      {/* Agent reasoning panel — shown when nodeResults available */}
      {Object.keys(editor.nodeResults).length > 0 && (
        <AgentReasoningPanel
          nodeResults={editor.nodeResults}
          expandedStep={expandedStep}
          onToggle={setExpandedStep}
          mode={editor.mode}
        />
      )}

      {/* Concept selection panel — shown after critic in creator mode */}
      {editor.isWaitingForConcept && editor.concepts && (
        <ConceptSelectionPanel
          candidates={editor.concepts}
          recommendedId={editor.recommendedConceptId}
          onSelect={(id) => editor.resume("select", undefined, id)}
          onRegenerate={() => editor.resume("regenerate")}
          onCustomConcept={(concept) =>
            editor.resume("custom_concept", undefined, undefined, { customConcept: concept })
          }
        />
      )}

      {/* Review approval panel — shown when waiting for user input */}
      {editor.isWaitingForInput && !editor.isWaitingForConcept && (
        <ReviewApprovalPanel
          scenes={editor.scenes}
          onApprove={() => editor.resume("approve")}
          onRevise={(feedback) => editor.resume("revise", feedback)}
          feedbackPresets={editor.feedbackPresets ?? undefined}
          onPresetRevise={(presetId, params) =>
            editor.resume("revise", undefined, undefined, {
              feedbackPreset: presetId,
              feedbackPresetParams: params,
            })
          }
          reviewResult={editor.nodeResults.review}
        />
      )}

      {/* Post-generation CTA */}
      {editor.justGenerated && !editor.isGenerating && !editor.isWaitingForInput && (
        <section className="flex items-center justify-between rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4">
          <div>
            <p className="text-sm font-medium text-emerald-900">
              스크립트 생성 완료 ({editor.scenes.length}개 씬)
            </p>
            <p className="mt-0.5 text-xs text-emerald-600">
              바로 영상을 제작하거나, 씬을 편집할 수 있습니다
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => useUIStore.getState().setActiveTab("edit")}
            >
              <PenLine className="h-3.5 w-3.5" />씬 편집하기
            </Button>
            <Button
              size="sm"
              variant="success"
              loading={isStarting}
              onClick={handleStartProduction}
            >
              <Play className="h-3.5 w-3.5" />
              영상 제작 시작
            </Button>
          </div>
        </section>
      )}

      {/* Feedback widget — shown after generation completes */}
      {editor.scenes.length > 0 && !editor.isGenerating && !editor.feedbackSubmitted && (
        <ScriptFeedbackWidget onSubmit={editor.submitFeedback} />
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
