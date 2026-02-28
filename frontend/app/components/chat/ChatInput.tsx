"use client";

import { useState, useRef, useCallback, type KeyboardEvent, type ChangeEvent } from "react";
import { SendHorizonal, Sparkles } from "lucide-react";

type Props = {
  onSend: (text: string) => Promise<void>;
  onGenerate: () => void;
  disabled: boolean;
  hasMessages: boolean;
  hasTopic: boolean;
};

const SUGGESTIONS = ["카페 알바생이 본 이별 장면", "첫 출근날 실수 모음", "오래된 친구와의 재회"];

const MAX_ROWS = 3;

export default function ChatInput({ onSend, onGenerate, disabled, hasMessages, hasTopic }: Props) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const showSuggestions = !hasMessages || (!text.trim() && !hasTopic);

  const adjustHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const lineHeight = 20;
    el.style.height = `${Math.min(el.scrollHeight, lineHeight * MAX_ROWS)}px`;
  }, []);

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    adjustHeight();
  };

  const handleSend = async () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    setText("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    await onSend(trimmed);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setText("");
    onSend(suggestion);
  };

  return (
    <div className="border-t border-zinc-100 bg-white px-4 pt-3 pb-4">
      {/* Suggestion chips */}
      {showSuggestions && (
        <div className="mb-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              disabled={disabled}
              onClick={() => handleSuggestionClick(s)}
              className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-xs text-zinc-600 transition-colors hover:border-zinc-300 hover:bg-zinc-50 disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Quick generate action */}
      {hasTopic && !disabled && (
        <button
          type="button"
          onClick={onGenerate}
          className="mb-3 flex items-center gap-1.5 rounded-full bg-gradient-to-r from-violet-500 to-purple-500 px-3.5 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90"
        >
          <Sparkles className="h-3.5 w-3.5" />
          이대로 생성
        </button>
      )}

      {/* Input row */}
      <div className="flex items-end gap-2 rounded-2xl border border-zinc-200 bg-zinc-50 px-3 py-2">
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="어떤 쇼츠를 만들까요?"
          className="flex-1 resize-none bg-transparent text-sm text-zinc-800 outline-none placeholder:text-zinc-400 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-white transition-colors hover:bg-zinc-700 disabled:opacity-30"
        >
          <SendHorizonal className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
