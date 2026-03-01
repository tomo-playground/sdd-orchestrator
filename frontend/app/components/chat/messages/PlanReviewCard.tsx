"use client";

import { memo, useState } from "react";
import type { ChatMessage } from "@/app/types/chat";
import type { ResumeAction, ResumeOptions } from "@/app/hooks/scriptEditor/types";

type Props = {
  message: ChatMessage;
  onResume: (
    action: ResumeAction,
    feedback?: string,
    conceptId?: number,
    options?: ResumeOptions
  ) => void;
};

const PlanReviewCard = memo(function PlanReviewCard({ message, onResume }: Props) {
  const [mode, setMode] = useState<"view" | "edit">("view");
  const [feedback, setFeedback] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const plan = message.directorPlan || {};
  const skipStages = message.skipStages || [];
  const creativeGoal = plan.creative_goal ? String(plan.creative_goal) : null;
  const targetEmotion = plan.target_emotion ? String(plan.target_emotion) : null;

  const handleProceed = () => {
    setSubmitted(true);
    onResume("proceed");
  };

  const handleRevise = () => {
    if (mode === "view") {
      setMode("edit");
      return;
    }
    if (!feedback.trim()) return;
    setSubmitted(true);
    onResume("revise_plan", feedback.trim());
  };

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <h3 className="mb-2 text-sm font-semibold text-blue-900">디렉터 플랜 검토</h3>

      {creativeGoal && (
        <div className="mb-2">
          <span className="text-xs font-medium text-blue-700">크리에이티브 목표</span>
          <p className="text-sm text-blue-900">{creativeGoal}</p>
        </div>
      )}

      {targetEmotion && (
        <div className="mb-2">
          <span className="text-xs font-medium text-blue-700">타겟 감정</span>
          <p className="text-sm text-blue-900">{targetEmotion}</p>
        </div>
      )}

      {skipStages.length > 0 && (
        <div className="mb-3">
          <span className="text-xs font-medium text-blue-700">스킵 단계</span>
          <div className="mt-1 flex flex-wrap gap-1">
            {skipStages.map((s) => (
              <span
                key={s}
                className="rounded-full bg-blue-100 px-2 py-0.5 text-[11px] text-blue-700"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {mode === "edit" && (
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="수정 요청 사항을 입력하세요..."
          className="mb-3 w-full rounded border border-blue-200 bg-white p-2 text-sm text-zinc-800 placeholder:text-zinc-400 focus:border-blue-400 focus:outline-none"
          rows={3}
          disabled={submitted}
        />
      )}

      {!submitted && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleProceed}
            className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            진행해주세요
          </button>
          <button
            type="button"
            onClick={handleRevise}
            className="rounded-lg border border-blue-300 bg-white px-4 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-50"
          >
            {mode === "edit" ? "수정 요청 전송" : "수정할게요"}
          </button>
        </div>
      )}

      {submitted && <p className="text-xs text-blue-600">요청이 전달되었습니다.</p>}
    </div>
  );
});

export default PlanReviewCard;
