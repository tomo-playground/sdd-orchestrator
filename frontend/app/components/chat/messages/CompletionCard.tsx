"use client";

import { useState, useCallback } from "react";
import { CheckCircle, ChevronDown, ChevronUp, Pencil, Play } from "lucide-react";
import Button from "../../ui/Button";
import { useStoryboardStore } from "../../../store/useStoryboardStore";
import type { CompletionMeta } from "../../../types/chat";

const STRUCTURE_LABELS: Record<string, string> = {
  monologue: "독백",
  dialogue: "대화형",
  narrated_dialogue: "내레이션 대화",
  confession: "고백",
};

const SPEAKER_COLORS: Record<string, string> = {
  A: "bg-emerald-100 text-emerald-700",
  B: "bg-blue-100 text-blue-700",
  Narrator: "bg-zinc-100 text-zinc-500",
};

type Props = {
  text: string;
  meta?: CompletionMeta;
  sceneCount: number;
  onNavigate: (tab: string) => void;
};

export default function CompletionCard({ text, meta, sceneCount, onNavigate }: Props) {
  const storeSceneCount = useStoryboardStore((s) => s.scenes.length);
  const effectiveCount = storeSceneCount || sceneCount;
  const [expanded, setExpanded] = useState(() => (meta?.sceneSummaries.length ?? 0) <= 5);

  // meta가 없으면 기존 간소 버전
  if (!meta) {
    return (
      <div className="flex gap-2">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100">
          <CheckCircle className="h-4 w-4 text-emerald-600" />
        </div>
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="text-sm font-medium text-emerald-900">{text}</p>
          <p className="mt-1 text-xs text-emerald-700">{effectiveCount}개 씬이 준비되었습니다.</p>
          <CompletionActions onNavigate={onNavigate} />
        </div>
      </div>
    );
  }

  const emotions = meta.sceneSummaries.map((s) => s.emotion).filter((e): e is string => !!e);

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100">
        <CheckCircle className="h-4 w-4 text-emerald-600" />
      </div>
      <div className="w-full max-w-md rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
        {/* 헤더 */}
        <p className="text-xs text-emerald-600">스크립트 생성 완료</p>

        {/* 제목 */}
        <p className="mt-1 truncate text-sm font-semibold text-emerald-900" title={meta.topic}>
          {meta.topic || "제목 없음"}
        </p>

        {/* 메타 배지 */}
        <div className="mt-2 flex flex-wrap gap-1.5">
          <span className="rounded-full border border-emerald-300 px-2 py-0.5 text-[11px] text-emerald-700">
            {STRUCTURE_LABELS[meta.structure] ?? meta.structure}
          </span>
          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] text-emerald-700">
            {meta.sceneSummaries.length}씬
          </span>
          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] text-emerald-700">
            {Math.round(meta.totalDuration)}초
          </span>
          {meta.characterAName && (
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] text-emerald-700">
              {meta.characterAName}
            </span>
          )}
          {meta.characterBName && (
            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[11px] text-blue-700">
              {meta.characterBName}
            </span>
          )}
        </div>

        {/* 씬 미리보기 */}
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex w-full items-center justify-between text-xs text-emerald-700 hover:text-emerald-900"
          >
            <span className="font-medium">씬 미리보기</span>
            {expanded ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </button>
          {expanded && (
            <div className="mt-1.5 space-y-0.5">
              {meta.sceneSummaries.map((s) => (
                <div key={s.order} className="flex items-center gap-1.5 text-[11px]">
                  <span className="w-4 text-right text-zinc-400">{s.order + 1}</span>
                  <span
                    className={`rounded px-1 py-0.5 text-[11px] font-medium ${SPEAKER_COLORS[s.speaker] ?? SPEAKER_COLORS.A}`}
                  >
                    {s.speaker}
                  </span>
                  <span className="w-6 text-zinc-400">{Math.round(s.duration)}s</span>
                  <span className="truncate text-zinc-700">&ldquo;{s.scriptPreview}&rdquo;</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 감정 흐름 */}
        {emotions.length > 0 && (
          <div className="mt-2 text-[11px] text-zinc-500">
            <span className="text-zinc-400">감정: </span>
            {emotions.map((e, i) => (
              <span key={i}>
                {i > 0 && <span className="mx-0.5 text-zinc-300">&rarr;</span>}
                <span className="text-emerald-700">{e}</span>
              </span>
            ))}
          </div>
        )}

        {/* 액션 버튼 */}
        <CompletionActions onNavigate={onNavigate} />
      </div>
    </div>
  );
}

function CompletionActions({ onNavigate }: { onNavigate: (tab: string) => void }) {
  const [navigated, setNavigated] = useState(false);

  const handleNavigate = useCallback(
    (tab: string) => {
      setNavigated(true);
      onNavigate(tab);
    },
    [onNavigate]
  );

  return (
    <div className="mt-3 flex gap-2">
      <Button
        size="sm"
        variant="outline"
        onClick={() => handleNavigate("direct")}
        disabled={navigated}
      >
        <Pencil className="h-3.5 w-3.5" />씬 편집하기
      </Button>
      <Button
        size="sm"
        variant="success"
        onClick={() => handleNavigate("stage")}
        disabled={navigated}
      >
        <Play className="h-3.5 w-3.5" />
        영상 제작 시작
      </Button>
    </div>
  );
}
