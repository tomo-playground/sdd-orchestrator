"use client";

import ChatMessageList from "./ChatMessageList";
import ChatInput from "./ChatInput";
import ProgressBar from "./ProgressBar";
import type { ChatScriptEditorActions } from "../../hooks/useChatScriptEditor";

type Props = {
  editor: ChatScriptEditorActions;
};

export default function ChatArea({ editor }: Props) {
  return (
    <div className="flex flex-1 flex-col">
      {/* Message list */}
      <ChatMessageList messages={editor.chatMessages} editor={editor} />

      {/* Progress bar (between messages and input) */}
      {editor.activeProgress && <ProgressBar progress={editor.activeProgress} />}

      {/* Input */}
      <ChatInput
        onSend={editor.sendMessage}
        onGenerate={editor.confirmAndGenerate}
        disabled={editor.isGenerating}
        hasMessages={editor.chatMessages.length > 1}
        hasTopic={!!editor.topic.trim()}
      />
    </div>
  );
}
