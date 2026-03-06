"use client";

import { useState } from "react";
import { Play, PenLine } from "lucide-react";
import { usePresets } from "../../hooks/usePresets";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";
import ScriptOptionsCard from "./ScriptOptionsCard";
import ConceptSelectionPanel from "./ConceptSelectionPanel";
import ReviewApprovalPanel from "./ReviewApprovalPanel";
import AgentReasoningPanel from "./AgentReasoningPanel";
import CastingBanner from "./CastingBanner";
import AiCastingSummary from "./AiCastingSummary";
import ScriptFeedbackWidget from "./ScriptFeedbackWidget";
import Button from "../ui/Button";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useUIStore } from "../../store/useUIStore";
import { persistStoryboard } from "../../store/actions/storyboardActions";
import type { ScriptEditorActions } from "../../hooks/useScriptEditor";

type Props = {
  editor: ScriptEditorActions;
};

export default function ManualScriptEditor({ editor }: Props) {
  const { presets, languages, durations } = usePresets();
  const { confirm, dialogProps } = useConfirm();
  const casting = useStoryboardStore((s) => s.castingRecommendation);
  const [isStarting, setIsStarting] = useState(false);
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  const handleAcceptCasting = () => {
    if (!casting) return;
    if (casting.character_a_id != null) {
      editor.setField("characterId", casting.character_a_id);
      editor.setField("characterName", casting.character_a_name);
    }
    if (casting.character_b_id != null) {
      editor.setField("characterBId", casting.character_b_id);
      editor.setField("characterBName", casting.character_b_name);
    }
    if (casting.structure) {
      editor.setField("structure", casting.structure);
    }
    useStoryboardStore.getState().set({ castingRecommendation: null, isDirty: true });
  };

  const handleDismissCasting = () => {
    useStoryboardStore.getState().set({ castingRecommendation: null, isDirty: true });
  };

  const handleGenerate = async () => {
    if (editor.scenes.length > 0) {
      const ok = await confirm({
        title: "스크립트 재생성",
        message: `기존 ${editor.scenes.length}개 씬이 교체됩니다. 계속하시겠습니까?`,
        confirmLabel: "재생성",
        variant: "danger",
      });
      if (!ok) return;
    }

    // 캐릭터 미선택 시 자동 캐스팅 확인
    if (!editor.characterId) {
      const ok = await confirm({
        title: "AI 자동 캐스팅",
        message: "캐릭터가 선택되지 않았습니다. AI가 토픽에 맞는 캐릭터를 자동 선택합니다.",
        confirmLabel: "자동 캐스팅으로 시작",
      });
      if (!ok) return;
    }

    editor.generate();
  };

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
      <ScriptOptionsCard
        editor={editor}
        presets={presets}
        languages={languages}
        durations={durations}
        onGenerate={handleGenerate}
        expandedStep={expandedStep}
        onStepClick={(id) => setExpandedStep((prev) => (prev === id ? null : id))}
      />

      {/* Casting recommendation banner */}
      {casting && (
        <CastingBanner
          casting={casting}
          onAccept={handleAcceptCasting}
          onDismiss={handleDismissCasting}
        />
      )}

      {/* Agent reasoning panel */}
      {Object.keys(editor.nodeResults).length > 0 && (
        <AgentReasoningPanel
          nodeResults={editor.nodeResults}
          expandedStep={expandedStep}
          onToggle={setExpandedStep}
          skipStages={editor.directorSkipStages}
        />
      )}

      {/* Concept selection — creator mode */}
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

      {/* Review approval — waiting for user input */}
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
          productionSnapshot={editor.productionSnapshot}
        />
      )}

      {/* AI casting summary — post-generation */}
      {editor.justGenerated && !editor.isGenerating && !editor.isWaitingForInput && casting && (
        <AiCastingSummary
          casting={casting}
          onGoToStage={() => useUIStore.getState().setActiveTab("stage")}
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
              onClick={() => useUIStore.getState().setActiveTab("direct")}
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

      {/* Feedback widget */}
      {editor.scenes.length > 0 && !editor.isGenerating && !editor.feedbackSubmitted && (
        <ScriptFeedbackWidget onSubmit={editor.submitFeedback} />
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
