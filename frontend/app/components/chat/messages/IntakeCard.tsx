"use client";

import { useState } from "react";
import { Bot, Sparkles } from "lucide-react";
import type { IntakeGateMessage } from "../../../types/chat";
import type { ResumeOptions } from "../../../hooks/scriptEditor/types";

type Props = {
  message: IntakeGateMessage;
  onResume: (
    action: "answer",
    feedback?: string,
    conceptId?: number,
    options?: ResumeOptions
  ) => void;
  isInteractive?: boolean;
};

export default function IntakeCard({ message, onResume, isInteractive = true }: Props) {
  const { analysis, questions } = message;

  const structureQ = questions.find((q) => q.key === "structure");
  const toneQ = questions.find((q) => q.key === "tone");
  const charQ = questions.find((q) => q.key === "characters");

  const [structure, setStructure] = useState(analysis.suggested_structure ?? "monologue");
  const [tone, setTone] = useState(analysis.suggested_tone ?? "intimate");
  const [charA, setCharA] = useState<number | undefined>(undefined);
  const [charB, setCharB] = useState<number | undefined>(undefined);

  // MULTI_CHAR_STRUCTURES 기준 동적 판단 — structure 선택 변경 시 자동 갱신
  const [submitted, setSubmitted] = useState(false);

  const MULTI_CHAR_STRUCTURES = new Set(["dialogue", "narrated_dialogue"]);
  const needsTwo = MULTI_CHAR_STRUCTURES.has(structure);
  const characters = charQ?.characters ?? [];

  const handleSubmit = () => {
    if (submitted) return;
    setSubmitted(true);
    onResume("answer", undefined, undefined, {
      intakeValue: {
        structure,
        tone,
        character_id: charA,
        character_b_id: needsTwo ? charB : undefined,
      },
    });
  };

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="min-w-0 flex-1 space-y-3">
        {/* AI 분석 결과 */}
        {analysis.reasoning && (
          <div className="flex items-start gap-2 rounded-lg bg-violet-50 p-3 text-sm text-violet-700">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{analysis.reasoning}</span>
          </div>
        )}

        {/* Structure 선택 */}
        {structureQ && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-zinc-700">{structureQ.message}</p>
            <div className="flex flex-wrap gap-2">
              {structureQ.options?.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => isInteractive && setStructure(opt.id)}
                  disabled={!isInteractive}
                  className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                    structure === opt.id
                      ? "border-violet-500 bg-violet-50 text-violet-700"
                      : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300"
                  } ${!isInteractive ? "opacity-60" : ""}`}
                >
                  <div className="font-medium">{opt.label}</div>
                  {opt.description && (
                    <div className="mt-0.5 text-xs text-zinc-500">{opt.description}</div>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Tone 선택 */}
        {toneQ && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-zinc-700">{toneQ.message}</p>
            <div className="flex flex-wrap gap-2">
              {toneQ.options?.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => isInteractive && setTone(opt.id)}
                  disabled={!isInteractive}
                  className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                    tone === opt.id
                      ? "border-amber-500 bg-amber-50 text-amber-700"
                      : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300"
                  } ${!isInteractive ? "opacity-60" : ""}`}
                >
                  <div className="font-medium">{opt.label}</div>
                  {opt.description && (
                    <div className="mt-0.5 text-xs text-zinc-500">{opt.description}</div>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 캐릭터 선택 */}
        {charQ && characters.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-zinc-700">{charQ.message}</p>
            <div className="space-y-1.5">
              <label className="text-xs text-zinc-500">캐릭터 A</label>
              <div className="flex flex-wrap gap-2">
                {characters.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => {
                      if (!isInteractive) return;
                      setCharA(c.id);
                      if (charB === c.id) setCharB(undefined);
                    }}
                    disabled={!isInteractive}
                    className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                      charA === c.id
                        ? "border-sky-500 bg-sky-50 text-sky-700"
                        : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300"
                    } ${!isInteractive ? "opacity-60" : ""}`}
                  >
                    {c.name}
                  </button>
                ))}
              </div>
              {needsTwo && (
                <>
                  <label className="text-xs text-zinc-500">캐릭터 B</label>
                  <div className="flex flex-wrap gap-2">
                    {characters
                      .filter((c) => c.id !== charA)
                      .map((c) => (
                        <button
                          key={c.id}
                          onClick={() => isInteractive && setCharB(c.id)}
                          disabled={!isInteractive}
                          className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                            charB === c.id
                              ? "border-sky-500 bg-sky-50 text-sky-700"
                              : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300"
                          } ${!isInteractive ? "opacity-60" : ""}`}
                        >
                          {c.name}
                        </button>
                      ))}
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* 확인 버튼 */}
        {isInteractive && !submitted && (
          <button
            onClick={handleSubmit}
            disabled={submitted}
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-700 disabled:opacity-50"
          >
            이대로 진행
          </button>
        )}
      </div>
    </div>
  );
}
