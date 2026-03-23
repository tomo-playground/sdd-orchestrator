"use client";

import { Bot, ExternalLink, RotateCcw } from "lucide-react";

type Props = {
  message: string;
  onRetry: () => void;
  traceUrl?: string;
};

function parseErrorMessage(raw: string): { display: string; hint?: string } {
  // PROHIBITED_CONTENT → 주제 변경 안내
  if (raw.includes("PROHIBITED") || raw.includes("prohibited")) {
    return {
      display: "콘텐츠 정책으로 생성이 차단되었습니다.",
      hint: "주제를 바꾸거나, 표현을 수정해 보세요.",
    };
  }

  // Try JSON format: {"message": "...", "detail": "..."}
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed.message === "string") return { display: parsed.message };
    if (typeof parsed.detail === "string") return { display: parsed.detail };
  } catch {}

  // Try Python dict format: "500: {'message': '...'}"
  const match = raw.match(/'message':\s*'([^']+)'/);
  if (match) return { display: match[1] };

  // Raw technical error → generic
  if (/^\d{3}:/.test(raw) || raw.includes("Traceback") || raw.length > 150) {
    return { display: "오류가 발생했습니다." };
  }

  return { display: raw };
}

export default function ErrorCard({ message, onRetry, traceUrl }: Props) {
  const { display, hint } = parseErrorMessage(message);

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3">
        <p className="text-sm text-red-800">{display}</p>
        {hint && <p className="mt-1 text-xs text-red-600">{hint}</p>}
        <div className="mt-2 flex items-center gap-3">
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-1 text-xs font-medium text-red-600 hover:text-red-800"
          >
            <RotateCcw className="h-3 w-3" />
            다시 시도
          </button>
          {traceUrl && (
            <a
              href={traceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-red-400 hover:text-red-600"
            >
              <ExternalLink className="h-3 w-3" />
              LangFuse에서 상세 보기
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
