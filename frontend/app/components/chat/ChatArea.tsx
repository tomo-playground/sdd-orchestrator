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
  const setPendingAutoRun = useUIStore((s) => s.setPendingAutoRun);
  const handleNavigate = useCallback(
    (tab: string) => {
      if (tab === "stage") {
        setPendingAutoRun(true);
      } else {
        setActiveTab(tab as StudioTab);
      }
    },
    [setActiveTab, setPendingAutoRun]
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

  const isInitialState = editor.chatMessages.length <= 1;

  return (
    <div className="flex flex-1 flex-col">
      {isInitialState ? (
        <div className="flex flex-1 flex-col items-center justify-center px-6">
          <div className="mb-6 text-center">
            <h2 className="text-lg font-semibold text-zinc-800">어떤 쇼츠를 만들까요?</h2>
            <p className="mt-1.5 text-sm text-zinc-500">
              주제를 입력하면 AI가 스크립트를 작성해 드려요
            </p>
          </div>
          <div className="w-full max-w-3xl">
            <ChatInput
              onSend={editor.sendMessage}
              disabled={editor.isGenerating}
              hasMessages={false}
              hasTopic={false}
              borderless
            />
          </div>
        </div>
      ) : (
        <>
          <ChatMessageList messages={editor.chatMessages} callbacks={callbacks} />

          {editor.activeProgress && <ProgressBar progress={editor.activeProgress} />}

          <ChatInput
            onSend={editor.sendMessage}
            disabled={editor.isGenerating}
            hasMessages={editor.chatMessages.length > 1}
            hasTopic={!!editor.topic.trim()}
          />
        </>
      )}
    </div>
  );
}
