"use client";

import { Bot } from "lucide-react";

type Props = {
  text: string;
};

export default function AssistantBubble({ text }: Props) {
  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-zinc-100 px-4 py-2.5 text-sm whitespace-pre-wrap text-zinc-800">
        {text}
      </div>
    </div>
  );
}
