"use client";

import { Bot } from "lucide-react";
import type { ChatMessage } from "../../../types/chat";

type Props = {
  message: ChatMessage;
};

export default function ClarificationCard({ message }: Props) {
  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="max-w-[85%] space-y-2 rounded-2xl border border-violet-200 bg-violet-50 p-4">
        {message.text && <p className="text-sm text-zinc-700">{message.text}</p>}
        {message.questions?.map((q, i) => (
          <p key={i} className="text-sm font-medium text-zinc-800">
            • {q}
          </p>
        ))}
      </div>
    </div>
  );
}
