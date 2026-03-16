"use client";

import { useState, useEffect } from "react";
import { useAutoScroll } from "../../hooks/useAutoScroll";
import ChatMessage from "./ChatMessage";
import type { ChatMessage as ChatMessageType } from "../../types/chat";
import type { ChatMessageCallbacks, ChatMessageData } from "./ChatMessage";

type Props = {
  messages: ChatMessageType[];
  callbacks: ChatMessageCallbacks;
  data: ChatMessageData;
};

export default function ChatMessageList({ messages, callbacks, data }: Props) {
  const lastTs = messages[messages.length - 1]?.timestamp ?? 0;
  const { containerRef, handleScroll } = useAutoScroll(messages.length, lastTs);

  // Zustand persist가 localStorage에서 채팅 히스토리를 로드하면
  // SSR 렌더링(웰컴 메시지)과 클라이언트(저장된 채팅)가 불일치 → hydration 가드
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      role="log"
      aria-live="polite"
      aria-label="채팅 메시지"
      className="scrollbar-hide flex-1 overflow-y-auto py-6"
    >
      {hydrated && (
        <div className="mx-auto max-w-3xl space-y-5 px-6">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} callbacks={callbacks} data={data} />
          ))}
          <div className="h-24 shrink-0" />
        </div>
      )}
    </div>
  );
}
