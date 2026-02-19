"use client";

import type { AgentMessageItem } from "../../../types";

type Props = {
  messages: AgentMessageItem[];
};

const TYPE_COLORS: Record<string, string> = {
  directive: "text-indigo-600",
  report: "text-emerald-600",
  feedback: "text-amber-600",
  revision: "text-rose-600",
};

export default function AgentMessagesSection({ messages }: Props) {
  if (!messages || messages.length === 0) return null;

  return (
    <div className="space-y-1.5">
      {messages.map((msg, i) => {
        const typeCls = TYPE_COLORS[msg.message_type ?? ""] ?? "text-zinc-500";
        return (
          <div key={i} className="rounded bg-zinc-50 px-2 py-1.5">
            <div className="flex items-center gap-1 text-[11px]">
              {msg.sender && <span className="font-medium text-zinc-600">{msg.sender}</span>}
              {msg.recipient && (
                <>
                  <span className="text-zinc-400">&rarr;</span>
                  <span className="font-medium text-zinc-600">{msg.recipient}</span>
                </>
              )}
              {msg.message_type && <span className={`ml-1 ${typeCls}`}>[{msg.message_type}]</span>}
            </div>
            {msg.content && (
              <p className="mt-0.5 text-[11px] leading-relaxed text-zinc-500">{msg.content}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
