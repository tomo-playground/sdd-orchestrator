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
    const trimmed = feedback.trim();
    if (!trimmed) return;
    setSubmitted(true);
    onResume("revise_plan", trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleRevise();
    }
  };

  const adjustHeight = (el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    const lineHeight = 20;
    el.style.height = `${Math.min(el.scrollHeight, lineHeight * 3)}px`;
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFeedback(e.target.value);
    adjustHeight(e.target);
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

      {mode === "edit" && !submitted ? (
        <div className="flex items-end gap-2 rounded-2xl border border-blue-200 bg-white px-3 py-2 focus-within:border-blue-400 focus-within:ring-1 focus-within:ring-blue-400 transition-shadow">
          <textarea
            value={feedback}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="수정 요청 사항을 입력하세요... (예: 감성적인 톤 추가)"
            className="flex-1 resize-none bg-transparent text-sm text-zinc-800 outline-none placeholder:text-zinc-400 min-h-[20px] pb-1"
            rows={1}
            autoFocus
          />
          <button
            type="button"
            onClick={handleRevise}
            disabled={!feedback.trim()}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:opacity-30 mb-0.5"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="m3 3 3 9-3 9 19-9ZM6 12h16" /></svg>
          </button>
        </div>
      ) : (
        !submitted && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleProceed}
              className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 transition"
            >
              진행해주세요
            </button>
            <button
              type="button"
              onClick={handleRevise}
              className="rounded-lg border border-blue-300 bg-white px-4 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-50 transition"
            >
              수정할게요
            </button>
          </div>
        )
      )}

      {submitted && <p className="text-xs text-blue-600">요청이 전달되었습니다.</p>}
    </div>
  );
});

export default PlanReviewCard;
