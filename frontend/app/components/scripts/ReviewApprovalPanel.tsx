"use client";

import { useState } from "react";
import { CheckCircle, Edit3 } from "lucide-react";
import Button from "../ui/Button";
import type { SceneItem } from "../../hooks/useScriptEditor";

type Props = {
  scenes: SceneItem[];
  onApprove: () => void;
  onRevise: (feedback: string) => void;
};

export default function ReviewApprovalPanel({ scenes, onApprove, onRevise }: Props) {
  const [feedback, setFeedback] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);

  return (
    <section className="mt-6 rounded-2xl border-2 border-amber-200 bg-amber-50/50 p-6">
      <h3 className="mb-3 text-sm font-semibold text-amber-800">검토 대기 중</h3>
      <p className="mb-4 text-xs text-amber-700">
        AI가 {scenes.length}개 씬을 생성했습니다. 승인하거나 수정을 요청하세요.
      </p>

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
    </section>
  );
}
