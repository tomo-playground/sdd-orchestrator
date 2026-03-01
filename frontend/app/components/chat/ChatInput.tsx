"use client";

import { useState, useRef, useCallback, type KeyboardEvent, type ChangeEvent } from "react";
import { SendHorizonal } from "lucide-react";

type InteractionMode = "auto" | "guided" | "hands_on";

type Props = {
  onSend: (text: string) => Promise<void>;
  disabled: boolean;
  hasMessages: boolean;
  hasTopic: boolean;
  borderless?: boolean;
  interactionMode?: InteractionMode;
  onModeChange?: (mode: InteractionMode) => void;
};

const SUGGESTIONS = ["카페 알바생이 본 이별 장면", "첫 출근날 실수 모음", "오래된 친구와의 재회"];

const MODE_OPTIONS = [
  { value: "auto" as const, label: "Auto" },
  { value: "guided" as const, label: "Guided" },
  { value: "hands_on" as const, label: "Hands-on" },
] as const;

const MAX_ROWS = 3;

export default function ChatInput({
  onSend,
  disabled,
  hasMessages,
  hasTopic,
  borderless,
  interactionMode,
  onModeChange,
}: Props) {
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
    <div
      className={borderless ? "bg-white pt-3 pb-4" : "border-t border-zinc-100 bg-white pt-3 pb-4"}
    >
      <div className="mx-auto max-w-3xl px-4">
        {/* Mode chips */}
        {interactionMode && onModeChange && (
          <div className="mb-2 flex gap-1.5">
            {MODE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                disabled={disabled}
                onClick={() => onModeChange(opt.value)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
                  interactionMode === opt.value
                    ? "border-zinc-800 bg-zinc-800 text-white"
                    : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300 hover:bg-zinc-50"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}

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

        {/* Input row */}
        <div className="flex items-end gap-2 rounded-2xl border border-zinc-200 bg-zinc-50 px-3 py-2">
          <textarea
            ref={textareaRef}
            data-chat-input
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
    </div>
  );
}
