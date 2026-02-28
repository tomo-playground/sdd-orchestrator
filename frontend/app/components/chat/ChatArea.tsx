"use client";

import { useCallback, useMemo } from "react";
import ChatMessageList from "./ChatMessageList";
import ChatInput from "./ChatInput";
import ProgressBar from "./ProgressBar";
import { useUIStore, type StudioTab } from "../../store/useUIStore";
import type { ChatScriptEditorActions } from "../../hooks/useChatScriptEditor";
import type { ChatMessageCallbacks } from "./ChatMessage";

type Props = {
  editor: ChatScriptEditorActions;
};

export default function ChatArea({ editor }: Props) {
  const setActiveTab = useUIStore((s) => s.setActiveTab);
  const handleNavigate = useCallback(
    (tab: string) => setActiveTab(tab as StudioTab),
    [setActiveTab]
  );

  const callbacks: ChatMessageCallbacks = useMemo(
    () => ({
      onApplyRecommendation: editor.applyRecommendation,
      onResume: editor.resume,
      onRetry: editor.confirmAndGenerate,
      onNavigate: handleNavigate,
      scenes: editor.scenes,
      feedbackPresets: editor.feedbackPresets,
    }),
    [
      editor.applyRecommendation,
      editor.resume,
      editor.confirmAndGenerate,
      handleNavigate,
      editor.scenes,
      editor.feedbackPresets,
    ]
  );

  return (
    <div className="flex flex-1 flex-col">
      <ChatMessageList messages={editor.chatMessages} callbacks={callbacks} />

      {editor.activeProgress && <ProgressBar progress={editor.activeProgress} />}

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
