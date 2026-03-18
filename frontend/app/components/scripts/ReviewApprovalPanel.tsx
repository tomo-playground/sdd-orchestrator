"use client";

import { useState } from "react";
import { CheckCircle, Edit3 } from "lucide-react";
import Button from "../ui/Button";
import FeedbackPresetButtons from "./FeedbackPresetButtons";
import NarrativeScoreChart from "./NarrativeScoreChart";
import DirectorPlanBanner from "./snapshot/DirectorPlanBanner";
import ProductionSnapshotSummary from "./snapshot/ProductionSnapshotSummary";
import type { SceneItem } from "../../hooks/useScriptEditor";
import type { FeedbackPreset, NarrativeScore, ProductionSnapshot } from "../../types";

function isNarrativeScore(v: unknown): v is NarrativeScore {
  return typeof v === "object" && v !== null && "overall" in v;
}

type Props = {
  scenes: SceneItem[];
  onApprove: () => void;
  onRevise: (feedback: string) => void;
  feedbackPresets?: FeedbackPreset[];
  onPresetRevise?: (presetId: string, params?: Record<string, string>) => void;
  reviewResult?: Record<string, unknown>;
  productionSnapshot?: ProductionSnapshot | null;
  /** true = 과거 메시지 → 액션 버튼 숨김 */
  disabled?: boolean;
};

export default function ReviewApprovalPanel({
  scenes,
  onApprove,
  onRevise,
  feedbackPresets,
  onPresetRevise,
  reviewResult,
  productionSnapshot,
  disabled = false,
}: Props) {
  const [feedback, setFeedback] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);

  // Phase 28-A: 0개 씬 → 에러 메시지 + 승인 버튼 제거
  if (scenes.length === 0) {
    return (
      <section className="mt-6 rounded-2xl border-2 border-red-200 bg-red-50/50 p-6">
        <h3 className="mb-3 text-sm font-semibold text-red-800">씬 생성 실패</h3>
        <p className="mb-4 text-xs text-red-700">
          AI가 씬을 생성하지 못했습니다. 주제를 변경하거나 수정을 요청해주세요.
        </p>
        <Button size="md" variant="secondary" onClick={() => setShowFeedback(true)}>
          <Edit3 className="h-4 w-4" />
          수정 요청
        </Button>
        {showFeedback && (
          <>
            <textarea
              className="mt-4 w-full rounded-lg border border-zinc-200 p-3 text-sm"
              rows={3}
              placeholder="수정 사항을 입력하세요..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
            />
            {feedback.trim() && (
              <Button
                size="md"
                variant="gradient"
                className="mt-2"
                onClick={() => onRevise(feedback.trim())}
              >
                전송
              </Button>
            )}
          </>
        )}
      </section>
    );
  }

  return (
    <section className="mt-6 rounded-2xl border-2 border-amber-200 bg-amber-50/50 p-6">
      <h3 className="mb-3 text-sm font-semibold text-amber-800">검토 대기 중</h3>
      <p className="mb-4 text-xs text-amber-700">
        AI가 {scenes.length}개 씬을 생성했습니다. 승인하거나 수정을 요청하세요.
      </p>

      {/* Narrative score compact — quality_gate에 이미 포함된 경우 중복 방지 */}
      {!productionSnapshot?.quality_gate?.narrative_score &&
        isNarrativeScore(reviewResult?.narrative_score) && (
          <div className="mb-3">
            <NarrativeScoreChart score={reviewResult.narrative_score} compact />
          </div>
        )}

      {/* Director Plan 배너 */}
      {productionSnapshot?.director_plan && (
        <DirectorPlanBanner plan={productionSnapshot.director_plan} />
      )}

      {/* Production 결과 요약 */}
      {productionSnapshot && Object.keys(productionSnapshot).length > 0 && (
        <ProductionSnapshotSummary snapshot={productionSnapshot} />
      )}

      {/* Scene preview */}
      <div className="mb-4 max-h-40 space-y-2 overflow-y-auto">
        {scenes.map((s) => (
          <div
            key={s.client_id ?? s.id}
            className="rounded-lg bg-white px-3 py-2 text-xs text-zinc-700"
          >
            <span className="font-medium text-zinc-400">#{s.order}</span> {s.script}
          </div>
        ))}
      </div>

      {disabled ? (
        <p className="text-xs text-amber-600">요청이 전달되었습니다.</p>
      ) : (
        <>
          {/* Feedback preset buttons */}
          {feedbackPresets && feedbackPresets.length > 0 && onPresetRevise && (
            <div className="mb-4">
              <FeedbackPresetButtons
                presets={feedbackPresets}
                onPresetSelect={onPresetRevise}
                onCustom={() => setShowFeedback(true)}
              />
            </div>
          )}

          {/* Feedback input */}
          {showFeedback && (
            <textarea
              className="mb-4 w-full rounded-lg border border-zinc-200 p-3 text-sm"
              rows={3}
              placeholder="수정 사항을 입력하세요..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
            />
          )}

          {/* Action buttons */}
          <div className="flex gap-3">
            <Button size="md" variant="gradient" onClick={onApprove}>
              <CheckCircle className="h-4 w-4" />
              승인
            </Button>
            <Button
              size="md"
              variant="secondary"
              onClick={() => {
                if (showFeedback && feedback.trim()) {
                  onRevise(feedback.trim());
                } else {
                  setShowFeedback(true);
                }
              }}
            >
              <Edit3 className="h-4 w-4" />
              수정 요청
            </Button>
          </div>
        </>
      )}
    </section>
  );
}
