"use client";

import { Bot } from "lucide-react";

type Props = {
  text: string;
};

// "스크립트를 생성하고 있습니다..." 처럼 생성 중 메시지는 "..."으로 끝남
// (useChatScriptEditor.ts: confirmAndGenerate / applyAndGenerate)
function isLoadingMessage(text: string): boolean {
  return text.endsWith("...");
}

function stripTrailingDots(text: string): string {
  return text.replace(/\.{3}$/, "");
}

export default function AssistantBubble({ text }: Props) {
  const loading = isLoadingMessage(text);
  const displayText = loading ? stripTrailingDots(text) : text;

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-zinc-100 px-4 py-2.5 text-sm whitespace-pre-wrap text-zinc-800">
        {displayText}
        {loading && (
          <span className="ml-0.5 inline-flex items-end gap-0.5">
            <span className="inline-block h-1 w-1 animate-bounce rounded-full bg-zinc-500 [animation-delay:0ms]" />
            <span className="inline-block h-1 w-1 animate-bounce rounded-full bg-zinc-500 [animation-delay:150ms]" />
            <span className="inline-block h-1 w-1 animate-bounce rounded-full bg-zinc-500 [animation-delay:300ms]" />
          </span>
        )}
      </div>
    </div>
  );
}
