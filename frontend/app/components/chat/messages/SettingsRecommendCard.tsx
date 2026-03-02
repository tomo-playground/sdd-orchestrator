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
    const trimmed = feedback.trim();
    if (!trimmed) return;
    setSubmitted(true);
    onSendMessage?.(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleRevise();
    }
  };

  const adjustHeight = (el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    const lineHeight = 20;
    el.style.height = `${Math.min(el.scrollHeight, lineHeight * 3)}px`;
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFeedback(e.target.value);
    adjustHeight(e.target);
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
          <div className="flex items-end gap-2 rounded-2xl border border-violet-200 bg-white px-3 py-2 focus-within:border-violet-400 focus-within:ring-1 focus-within:ring-violet-400 transition-shadow">
            <textarea
              value={feedback}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder="수정 요청을 입력하세요. 예: 소라로 캐릭터 변경, 60초로 늘려줘"
              className="flex-1 resize-none bg-transparent text-sm text-zinc-800 outline-none placeholder:text-zinc-400 min-h-[20px] pb-1"
              rows={1}
              autoFocus
            />
            <button
              type="button"
              onClick={handleRevise}
              disabled={!feedback.trim()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-600 text-white transition-colors hover:bg-violet-700 disabled:opacity-30 mb-0.5"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="m3 3 3 9-3 9 19-9ZM6 12h16" /></svg>
            </button>
          </div>
        )}

        {submitted && (
          <p className="text-xs text-violet-600 px-2">수정 요청이 전달되었습니다.</p>
        )}

        {!applied && !submitted && mode === "view" && (
          <div className="flex gap-2">
            <Button size="sm" variant="primary" className="flex-1" onClick={handleGenerate}>
              <Sparkles className="h-3.5 w-3.5" />
              스크립트 생성
            </Button>
            <Button size="sm" variant="secondary" onClick={handleRevise}>
              <MessageSquare className="h-3.5 w-3.5" />
              수정할게요
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
