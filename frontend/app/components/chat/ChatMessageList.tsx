"use client";

import { useAutoScroll } from "../../hooks/useAutoScroll";
import ChatMessage from "./ChatMessage";
import type { ChatMessage as ChatMessageType } from "../../types/chat";
import type { ChatScriptEditorActions } from "../../hooks/useChatScriptEditor";

type Props = {
  messages: ChatMessageType[];
  editor: ChatScriptEditorActions;
};

export default function ChatMessageList({ messages, editor }: Props) {
  const { containerRef, handleScroll } = useAutoScroll(messages);

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 space-y-4 overflow-y-auto px-4 py-6"
    >
      {messages.map((msg) => (
        <ChatMessage key={msg.id} message={msg} editor={editor} />
      ))}
    </div>
  );
}
