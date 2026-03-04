"use client";

import { memo, useState } from "react";
import type { PipelineStepMessage } from "@/app/types/chat";
import { ChevronDown, ChevronRight, Bot, AlertTriangle } from "lucide-react";

const NODE_LABELS: Record<string, string> = {
  director_plan: "디렉터 계획",
  research: "리서치",
  critic: "컨셉 토론",
  writer: "대본 생성",
  review: "리뷰",
  revise: "수정",
  cinematographer: "비주얼 디자인",
  tts_designer: "음성 디자인",
  sound_designer: "BGM 설계",
  copyright_reviewer: "저작권 검토",
  director: "통합 검증",
};

function hasContent(obj?: Record<string, unknown>): boolean {
  if (!obj) return false;
  return Object.values(obj).some(
    (v) => v !== null && v !== undefined && !(Array.isArray(v) && v.length === 0)
  );
}

function extractSummary(nodeName: string, result?: Record<string, unknown>): string {
  if (!result) return "처리 중...";
  switch (nodeName) {
    case "director_plan": {
      const plan = result.director_plan as Record<string, unknown> | undefined;
      return plan?.creative_goal ? String(plan.creative_goal) : "계획 수립 완료";
    }
    case "critic": {
      const cr = result.result as Record<string, unknown> | undefined;
      const candidates = Array.isArray(cr?.candidates) ? cr.candidates : [];
      return `${candidates.length}개 컨셉 생성`;
    }
    case "writer": {
      const scenes = Array.isArray(result.scenes) ? result.scenes : [];
      return `${scenes.length}개 씬 작성`;
    }
    case "review":
      return result.passed ? "통과" : "수정 필요";
    case "revise":
      return "수정 완료";
    case "cinematographer":
      return "비주얼 디자인 완료";
    case "tts_designer": {
      const designs = Array.isArray(result.tts_designs) ? result.tts_designs : [];
      return `${designs.length}개 음성 디자인`;
    }
    case "sound_designer": {
      const rec = result.recommendation as Record<string, unknown> | undefined;
      return rec?.mood ? `BGM: ${String(rec.mood)}` : "BGM 설계 완료";
    }
    case "copyright_reviewer":
      return result.overall ? `판정: ${String(result.overall)}` : "검토 완료";
    case "research": {
      const brief = result.brief as Record<string, unknown> | undefined;
      return brief?.topic_summary ? String(brief.topic_summary) : "리서치 완료";
    }
    case "director":
      return result.decision === "approve" ? "승인" : "수정 요청";
    default:
      return "완료";
  }
}

function hasFallback(result?: Record<string, unknown>): boolean {
  if (!result) return false;
  return result.fallback_reason !== undefined;
}

type Props = { message: PipelineStepMessage };

const PipelineStepCard = memo(function PipelineStepCard({ message }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { nodeName, nodeResult } = message;
  const label = NODE_LABELS[nodeName] || nodeName;
  const summary = extractSummary(nodeName, nodeResult);
  const expandable = hasContent(nodeResult);
  const isFallback = hasFallback(nodeResult);

  return (
    <div className="flex items-start gap-2 py-1">
      <Bot className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400" />
      <div className="min-w-0 flex-1">
        <button
          type="button"
          onClick={() => expandable && setExpanded((p) => !p)}
          aria-expanded={expanded}
          className={`flex items-center gap-1 text-xs ${
            expandable
              ? "cursor-pointer text-zinc-500 hover:text-zinc-700"
              : "cursor-default text-zinc-400"
          }`}
        >
          {expandable &&
            (expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />)}
          <span className="font-medium text-zinc-600">{label}</span>
          <span className="text-zinc-400">&mdash;</span>
          <span>{summary}</span>
          {isFallback && (
            <span className="ml-1 inline-flex items-center gap-0.5 rounded bg-amber-100 px-1.5 py-0.5 text-[11px] text-amber-700">
              <AlertTriangle className="h-3 w-3" />
              fallback
            </span>
          )}
        </button>
        {expanded && expandable && (
          <pre className="mt-1.5 max-h-40 overflow-auto rounded border border-zinc-200 bg-zinc-50 p-2 text-[11px] text-zinc-600">
            {JSON.stringify(nodeResult, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
});

export default PipelineStepCard;
