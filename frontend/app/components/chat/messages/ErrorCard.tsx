"use client";

import { Bot, RotateCcw } from "lucide-react";

type Props = {
  message?: string;
  onRetry: () => void;
};

function parseErrorMessage(raw?: string): string {
  if (!raw) return "오류가 발생했습니다.";

  // Try JSON format: {"message": "...", "detail": "..."}
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed.message === "string") return parsed.message;
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {}

  // Try Python dict format: "500: {'message': '...'}"
  const match = raw.match(/'message':\s*'([^']+)'/);
  if (match) return match[1];

  // If it looks like a raw technical error, use generic
  if (/^\d{3}:/.test(raw) || raw.includes("Traceback") || raw.length > 150) {
    return "오류가 발생했습니다.";
  }

  return raw;
}

export default function ErrorCard({ message, onRetry }: Props) {
  const displayMessage = parseErrorMessage(message);

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3">
        <p className="text-sm text-red-800">{displayMessage}</p>
        <button
          onClick={onRetry}
          className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-red-600 hover:text-red-800"
        >
          <RotateCcw className="h-3 w-3" />
          다시 시도
        </button>
      </div>
    </div>
  );
}
