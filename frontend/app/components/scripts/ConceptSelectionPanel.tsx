"use client";

import { useState } from "react";
import { Lightbulb, Check, RefreshCw, PenLine } from "lucide-react";
import Button from "../ui/Button";
import type { ConceptCandidate } from "../../types";

type Props = {
  candidates: ConceptCandidate[];
  recommendedId: number | null;
  onSelect: (conceptId: number) => void;
  onRegenerate?: () => void;
  onCustomConcept?: (concept: { title: string; concept: string }) => void;
};

export default function ConceptSelectionPanel({
  candidates,
  recommendedId,
  onSelect,
  onRegenerate,
  onCustomConcept,
}: Props) {
  const [selectedId, setSelectedId] = useState<number | null>(recommendedId);
  const [showCustom, setShowCustom] = useState(false);
  const [customTitle, setCustomTitle] = useState("");
  const [customConcept, setCustomConcept] = useState("");

  return (
    <section className="space-y-4 rounded-2xl border border-amber-200 bg-amber-50 p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-amber-600" />
          <h3 className="text-sm font-semibold text-amber-900">컨셉 선택</h3>
          <span className="text-xs text-amber-600">
            AI가 {candidates.length}개 컨셉을 제안했습니다
          </span>
        </div>
        <div className="flex gap-2">
          {onRegenerate && (
            <Button size="sm" variant="outline" onClick={onRegenerate}>
              <RefreshCw className="h-3.5 w-3.5" />
              다시 생성
            </Button>
          )}
          {onCustomConcept && (
            <Button size="sm" variant="outline" onClick={() => setShowCustom(!showCustom)}>
              <PenLine className="h-3.5 w-3.5" />
              직접 입력
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {candidates.map((c, i) => {
          const isSelected = selectedId === i;
          const isRecommended = recommendedId === i;
          return (
            <button
              key={i}
              type="button"
              onClick={() => setSelectedId(i)}
              className={`relative rounded-xl border-2 p-4 text-left transition-all ${
                isSelected
                  ? "border-amber-500 bg-white shadow-md"
                  : "border-zinc-200 bg-white hover:border-amber-300"
              }`}
            >
              {isRecommended && (
                <span className="absolute -top-2 right-2 rounded-full bg-amber-500 px-2 py-0.5 text-[11px] font-medium text-white">
                  AI 추천
                </span>
              )}
              {isSelected && <Check className="absolute top-2 right-2 h-4 w-4 text-amber-600" />}
              <p className="text-sm font-semibold text-zinc-900">{c.title}</p>
              <p className="mt-1 text-xs leading-relaxed text-zinc-600">{c.concept}</p>
              {c.strengths && c.strengths.length > 0 && (
                <div className="mt-2">
                  <p className="text-[11px] font-medium text-emerald-700">강점</p>
                  <ul className="mt-0.5 space-y-0.5">
                    {c.strengths.slice(0, 2).map((s, j) => (
                      <li key={j} className="text-[11px] text-emerald-600">
                        + {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Custom concept form */}
      {showCustom && onCustomConcept && (
        <div className="space-y-2 rounded-lg border border-amber-200 bg-white p-3">
          <input
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            placeholder="컨셉 제목"
            value={customTitle}
            onChange={(e) => setCustomTitle(e.target.value)}
          />
          <textarea
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            rows={2}
            placeholder="컨셉 설명"
            value={customConcept}
            onChange={(e) => setCustomConcept(e.target.value)}
          />
          <div className="flex justify-end">
            <Button
              size="sm"
              variant="gradient"
              disabled={!customTitle.trim() || !customConcept.trim()}
              onClick={() =>
                onCustomConcept({ title: customTitle.trim(), concept: customConcept.trim() })
              }
            >
              이 컨셉으로 진행
            </Button>
          </div>
        </div>
      )}

      {!showCustom && (
        <div className="flex justify-end">
          <Button
            size="sm"
            variant="gradient"
            disabled={selectedId === null}
            onClick={() => selectedId !== null && onSelect(selectedId)}
          >
            이 컨셉으로 진행
          </Button>
        </div>
      )}
    </section>
  );
}
