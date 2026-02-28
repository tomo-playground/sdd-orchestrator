"use client";

import { useAutoScroll } from "../../hooks/useAutoScroll";
import ChatMessage from "./ChatMessage";
import type { ChatMessage as ChatMessageType } from "../../types/chat";
import type { ChatMessageCallbacks } from "./ChatMessage";

type Props = {
  messages: ChatMessageType[];
  callbacks: ChatMessageCallbacks;
};

export default function ChatMessageList({ messages, callbacks }: Props) {
  const { containerRef, handleScroll } = useAutoScroll(messages);

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto py-6"
    >
      <div className="mx-auto max-w-3xl space-y-5 px-6">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} callbacks={callbacks} />
        ))}
        <div className="h-24 shrink-0" />
      </div>
    </div>
  );
}
