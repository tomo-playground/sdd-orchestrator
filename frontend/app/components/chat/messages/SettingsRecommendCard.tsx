"use client";

import { useState } from "react";
import { Bot, Check, Sparkles, MessageSquare } from "lucide-react";
import Button from "../../ui/Button";
import type { ChatMessage, SettingsRecommendation } from "../../../types/chat";

type Props = {
  message: ChatMessage;
  onApplyAndGenerate: (rec: SettingsRecommendation) => void;
  onSendMessage?: (text: string) => void;
};

function structureLabel(structure: string): string {
  const map: Record<string, string> = {
    Monologue: "독백 (1인)",
    Dialogue: "대화 (2인)",
    Confession: "고백 (1인)",
    Narrated_Dialogue: "나레이션 대화 (2인)",
  };
  return map[structure] ?? structure;
}

function formatCharacters(rec: SettingsRecommendation): string {
  if (!rec.character_name) return "미정";
  if (rec.character_b_name) return `${rec.character_name}, ${rec.character_b_name}`;
  return rec.character_name;
}

export default function SettingsRecommendCard({ message, onApplyAndGenerate, onSendMessage }: Props) {
  const [applied, setApplied] = useState(false);
  const [mode, setMode] = useState<"view" | "edit">("view");
  const [feedback, setFeedback] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const rec = message.recommendation;
  if (!rec) return null;

  const handleGenerate = () => {
    onApplyAndGenerate(rec);
    setApplied(true);
  };

  const handleRevise = () => {
    if (mode === "view") {
      setMode("edit");
      return;
    }
    if (!feedback.trim()) return;
    setSubmitted(true);
    onSendMessage?.(feedback.trim());
  };

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="max-w-[85%] space-y-3 rounded-2xl border border-violet-200 bg-violet-50 p-4">
        <p className="text-sm text-zinc-700">{rec.reasoning}</p>

        <ul className="space-y-1 rounded-xl bg-white p-3 text-sm text-zinc-700">
          <li>
            <span className="font-medium text-zinc-500">구성:</span> {structureLabel(rec.structure)}
          </li>
          <li>
            <span className="font-medium text-zinc-500">길이:</span> {rec.duration}초
          </li>
          <li>
            <span className="font-medium text-zinc-500">캐릭터:</span> {formatCharacters(rec)}
          </li>
          <li>
            <span className="font-medium text-zinc-500">언어:</span> {rec.language}
          </li>
        </ul>

        {mode === "edit" && !submitted && (
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="수정 요청을 입력하세요. 예: 소라로 캐릭터 변경, 60초로 늘려줘"
            className="w-full rounded-xl border border-violet-200 bg-white p-2 text-sm text-zinc-800 placeholder:text-zinc-400 focus:border-violet-400 focus:outline-none"
            rows={2}
            autoFocus
          />
        )}

        {submitted && (
          <p className="text-xs text-violet-600">수정 요청이 전달되었습니다.</p>
        )}

        {!applied && !submitted && (
          <div className="flex gap-2">
            <Button size="sm" variant="primary" className="flex-1" onClick={handleGenerate}>
              <Sparkles className="h-3.5 w-3.5" />
              스크립트 생성
            </Button>
            <Button size="sm" variant="secondary" onClick={handleRevise}>
              <MessageSquare className="h-3.5 w-3.5" />
              {mode === "edit" ? "요청 전송" : "수정할게요"}
            </Button>
          </div>
        )}

        {applied && (
          <Button size="sm" variant="secondary" className="w-full" disabled>
            <Check className="h-3.5 w-3.5" />
            생성 시작됨
          </Button>
        )}
      </div>
    </div>
  );
}
