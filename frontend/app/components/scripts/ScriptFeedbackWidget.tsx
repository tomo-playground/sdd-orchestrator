"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown, Send } from "lucide-react";
import Button from "../ui/Button";

type Props = {
  onSubmit: (rating: "positive" | "negative", feedbackText?: string) => Promise<void>;
};

export default function ScriptFeedbackWidget({ onSubmit }: Props) {
  const [rating, setRating] = useState<"positive" | "negative" | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!rating) return;
    setIsSubmitting(true);
    await onSubmit(rating, feedbackText.trim() || undefined);
    setIsSubmitting(false);
  };

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4">
      <p className="mb-3 text-sm font-medium text-zinc-700">생성된 스크립트가 마음에 드셨나요?</p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setRating("positive")}
          className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors ${
            rating === "positive"
              ? "border-emerald-300 bg-emerald-50 text-emerald-700"
              : "border-zinc-200 text-zinc-500 hover:border-zinc-300"
          }`}
        >
          <ThumbsUp className="h-4 w-4" />
          좋아요
        </button>
        <button
          type="button"
          onClick={() => setRating("negative")}
          className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors ${
            rating === "negative"
              ? "border-red-300 bg-red-50 text-red-700"
              : "border-zinc-200 text-zinc-500 hover:border-zinc-300"
          }`}
        >
          <ThumbsDown className="h-4 w-4" />
          아쉬워요
        </button>
      </div>
      {rating && (
        <div className="mt-3 space-y-2">
          <textarea
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            placeholder="추가 의견이 있다면 남겨주세요 (선택)"
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
            rows={2}
          />
          <div className="flex justify-end">
            <Button size="sm" variant="primary" onClick={handleSubmit} disabled={isSubmitting}>
              <Send className="h-3.5 w-3.5" />
              제출
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
