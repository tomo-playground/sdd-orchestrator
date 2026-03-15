"use client";

import { Bot } from "lucide-react";

type Props = {
  text: string;
};

/** Typing indicator bubble — 바운싱 dot 애니메이션과 함께 hint 텍스트를 표시 */
export default function TypingBubble({ text }: Props) {
  // hint 텍스트 끝의 "..."은 애니메이션 dot으로 대체
  const displayText = text.replace(/\.{3}$/, "");

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-zinc-100 px-4 py-2.5 text-sm whitespace-pre-wrap text-zinc-800">
        {displayText}
        <span className="ml-0.5 inline-flex items-end gap-0.5">
          <span className="inline-block h-1 w-1 animate-bounce rounded-full bg-zinc-500 [animation-delay:0ms]" />
          <span className="inline-block h-1 w-1 animate-bounce rounded-full bg-zinc-500 [animation-delay:150ms]" />
          <span className="inline-block h-1 w-1 animate-bounce rounded-full bg-zinc-500 [animation-delay:300ms]" />
        </span>
      </div>
    </div>
  );
}
