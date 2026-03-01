"use client";

import { memo, useState } from "react";
import type { ChatMessage } from "@/app/types/chat";
import { ChevronDown, ChevronRight, Bot } from "lucide-react";

const NODE_LABELS: Record<string, string> = {
  director_plan: "디렉터 계획",
  critic: "컨셉 토론",
  writer: "대본 생성",
  cinematographer: "비주얼 디자인",
  director: "통합 검증",
};

function extractSummary(nodeName: string, result?: Record<string, unknown>): string {
  if (!result) return "처리 중...";
  switch (nodeName) {
    case "director_plan":
      return result.creative_goal ? String(result.creative_goal) : "계획 수립 완료";
    case "critic": {
      const candidates = Array.isArray(result.candidates) ? result.candidates : [];
      return `${candidates.length}개 컨셉 생성`;
    }
    case "writer": {
      const scenes = Array.isArray(result.scenes) ? result.scenes : [];
      return `${scenes.length}개 씬 작성`;
    }
    case "cinematographer":
      return "비주얼 디자인 완료";
    case "director":
      return result.decision === "approve" ? "승인" : "수정 요청";
    default:
      return "완료";
  }
}

type Props = { message: ChatMessage };

const PipelineStepCard = memo(function PipelineStepCard({ message }: Props) {
  const [expanded, setExpanded] = useState(false);
  const nodeName = message.nodeName ?? "";
  const label = NODE_LABELS[nodeName] || nodeName;
  const summary = extractSummary(nodeName, message.nodeResult);

  return (
    <div className="flex items-start gap-2 py-1">
      <Bot className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400" />
      <div className="min-w-0 flex-1">
        <button
          type="button"
          onClick={() => setExpanded((p) => !p)}
          className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-700"
        >
          {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          <span className="font-medium text-zinc-600">{label}</span>
          <span className="text-zinc-400">&mdash;</span>
          <span>{summary}</span>
        </button>
        {expanded && message.nodeResult && (
          <pre className="mt-1.5 max-h-40 overflow-auto rounded border border-zinc-200 bg-zinc-50 p-2 text-[11px] text-zinc-600">
            {JSON.stringify(message.nodeResult, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
});

export default PipelineStepCard;
