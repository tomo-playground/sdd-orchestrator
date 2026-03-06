"use client";

import { memo, useState } from "react";
import type { PipelineStepMessage } from "@/app/types/chat";
import { ChevronDown, ChevronRight, Bot, AlertTriangle, AlertCircle, CheckCircle2 } from "lucide-react";

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
  explain: "창작 결정 설명",
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
    case "review": {
      const errors = Array.isArray(result.errors) ? result.errors : [];
      const warnings = Array.isArray(result.warnings) ? result.warnings : [];
      if (result.passed) return "통과";
      return `수정 필요 (오류 ${errors.length}건${warnings.length ? `, 경고 ${warnings.length}건` : ""})`;
    }
    case "revise": {
      const revised = Array.isArray(result.scenes) ? result.scenes : [];
      return revised.length > 0 ? `${revised.length}개 씬 수정 완료` : "수정 완료";
    }
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
    case "explain": {
      const exp = result.explanation as Record<string, unknown> | undefined;
      const decisions = Array.isArray(exp?.key_decisions) ? exp.key_decisions : [];
      return decisions.length > 0 ? `핵심 결정 ${decisions.length}건` : "분석 완료";
    }
    case "director": {
      const score = typeof result.director_checkpoint_score === "number"
        ? ` (${(result.director_checkpoint_score * 100).toFixed(0)}점)`
        : "";
      return result.decision === "approve" ? `승인${score}` : `수정 요청${score}`;
    }
    default:
      return "완료";
  }
}

function hasFallback(result?: Record<string, unknown>): boolean {
  if (!result) return false;
  return result.fallback_reason !== undefined;
}

const EXPLAIN_SECTIONS: { key: string; label: string }[] = [
  { key: "visual_strategy", label: "비주얼 전략" },
  { key: "audio_strategy", label: "오디오 전략" },
  { key: "quality_tradeoffs", label: "품질 트레이드오프" },
  { key: "overall_coherence", label: "전체 일관성" },
];

function ExplainDetail({ result }: { result: Record<string, unknown> }) {
  const exp = (result.explanation ?? result) as Record<string, unknown>;
  const decisions = Array.isArray(exp.key_decisions) ? (exp.key_decisions as string[]) : [];

  return (
    <div className="mt-1.5 space-y-2 rounded border border-zinc-200 bg-zinc-50 p-2 text-[11px] text-zinc-600">
      {EXPLAIN_SECTIONS.map(({ key, label }) => {
        const val = exp[key];
        if (!val) return null;
        return (
          <div key={key}>
            <span className="font-semibold text-zinc-700">{label}</span>
            <p className="mt-0.5 whitespace-pre-wrap">{String(val)}</p>
          </div>
        );
      })}
      {decisions.length > 0 && (
        <div>
          <span className="font-semibold text-zinc-700">핵심 결정</span>
          <ul className="mt-0.5 list-inside list-disc space-y-0.5">
            {decisions.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ReviewDetail({ result }: { result: Record<string, unknown> }) {
  const errors = Array.isArray(result.errors) ? (result.errors as string[]) : [];
  const warnings = Array.isArray(result.warnings) ? (result.warnings as string[]) : [];
  const ns = result.narrative_score as Record<string, unknown> | undefined;
  const gemini = result.gemini_feedback as string | undefined;

  return (
    <div className="mt-1.5 space-y-1.5 rounded border border-zinc-200 bg-zinc-50 p-2 text-[11px] text-zinc-600">
      {errors.length > 0 && (
        <div>
          <span className="flex items-center gap-1 font-semibold text-red-600">
            <AlertCircle className="h-3 w-3" /> 오류 {errors.length}건
          </span>
          <ul className="mt-0.5 list-inside list-disc space-y-0.5 text-red-700">
            {errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}
      {warnings.length > 0 && (
        <div>
          <span className="flex items-center gap-1 font-semibold text-amber-600">
            <AlertTriangle className="h-3 w-3" /> 경고 {warnings.length}건
          </span>
          <ul className="mt-0.5 list-inside list-disc space-y-0.5 text-amber-700">
            {warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}
      {gemini && (
        <div>
          <span className="font-semibold text-zinc-700">Gemini 피드백</span>
          <p className="mt-0.5 whitespace-pre-wrap">{gemini}</p>
        </div>
      )}
      {ns && typeof ns.overall === "number" && (
        <div>
          <span className="font-semibold text-zinc-700">서사 품질</span>
          <span className="ml-1 text-zinc-500">{(ns.overall * 100).toFixed(0)}점</span>
          {typeof ns.feedback === "string" && ns.feedback && (
            <p className="mt-0.5 whitespace-pre-wrap text-zinc-500">{ns.feedback}</p>
          )}
        </div>
      )}
    </div>
  );
}

function DirectorDetail({ result }: { result: Record<string, unknown> }) {
  const feedback = result.feedback || result.director_checkpoint_feedback;
  const score = typeof result.director_checkpoint_score === "number"
    ? result.director_checkpoint_score : null;

  return (
    <div className="mt-1.5 space-y-1.5 rounded border border-zinc-200 bg-zinc-50 p-2 text-[11px] text-zinc-600">
      {score !== null && (
        <div className="flex items-center gap-2">
          <span className="font-semibold text-zinc-700">품질 점수</span>
          <span className={`font-mono ${score >= 0.7 ? "text-green-600" : "text-amber-600"}`}>
            {(score * 100).toFixed(0)}점
          </span>
        </div>
      )}
      {typeof feedback === "string" && feedback && (
        <div>
          <span className="font-semibold text-zinc-700">피드백</span>
          <p className="mt-0.5 whitespace-pre-wrap">{feedback}</p>
        </div>
      )}
    </div>
  );
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
          nodeName === "explain" ? <ExplainDetail result={nodeResult} />
          : nodeName === "review" ? <ReviewDetail result={nodeResult} />
          : nodeName === "director" ? <DirectorDetail result={nodeResult} />
          : (
            <pre className="mt-1.5 max-h-40 overflow-auto rounded border border-zinc-200 bg-zinc-50 p-2 text-[11px] text-zinc-600">
              {JSON.stringify(nodeResult, null, 2)}
            </pre>
          )
        )}
      </div>
    </div>
  );
});

export default PipelineStepCard;
