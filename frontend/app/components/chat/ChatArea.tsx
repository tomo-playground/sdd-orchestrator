"use client";

import { useCallback, useMemo, useSyncExternalStore } from "react";
import ChatMessageList from "./ChatMessageList";
import ChatInput from "./ChatInput";
import ProgressBar from "./ProgressBar";
import { useUIStore, type StudioTab } from "../../store/useUIStore";
import type { ChatScriptEditorActions } from "../../hooks/useChatScriptEditor";
import type { ChatMessageCallbacks, ChatMessageData } from "./ChatMessage";

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
      onApplyAndGenerate: editor.applyAndGenerate,
      onResume: editor.resume,
      onRetry: editor.confirmAndGenerate,
      onNavigate: handleNavigate,
      onSendMessage: editor.sendMessage,
      onAcceptEdit: editor.applySceneEdits,
      onRejectEdit: editor.rejectSceneEdit,
    }),
    [
      editor.applyAndGenerate,
      editor.resume,
      editor.confirmAndGenerate,
      handleNavigate,
      editor.sendMessage,
      editor.applySceneEdits,
      editor.rejectSceneEdit,
    ]
  );

  const lastContentType = editor.chatMessages[editor.chatMessages.length - 1]?.contentType;
  const data: ChatMessageData = useMemo(
    () => ({
      scenes: editor.scenes,
      feedbackPresets: editor.feedbackPresets,
      hasError: lastContentType === "error",
    }),
    [editor.scenes, editor.feedbackPresets, lastContentType]
  );

  // Zustand persist hydration 가드: SSR에서는 항상 초기 상태(빈 채팅)로 렌더
  // → 클라이언트 hydration 후 실제 메시지로 전환 (hydration mismatch 방지)
  const hydrated = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
  const isInitialState =
    !hydrated || (editor.chatMessages.length <= 1 && editor.scenes.length === 0);
  const isEditMode = useMemo(
    () =>
      editor.chatMessages.some((m) => m.contentType === "completion") && editor.scenes.length > 0,
    [editor.chatMessages, editor.scenes.length]
  );

  return (
    <div className="flex h-full flex-col">
      {isInitialState ? (
        <div className="flex flex-1 flex-col items-center justify-center px-6">
          <div className="mb-6 text-center">
            <h2 className="text-lg font-semibold text-zinc-800">어떤 쇼츠를 만들까요?</h2>
            <p className="mt-1.5 text-sm text-zinc-500">
              주제를 입력하면 AI가 최적의 설정을 추천해 드려요
            </p>
          </div>
          <div className="w-full max-w-3xl">
            <ChatInput
              onSend={editor.sendMessage}
              disabled={editor.isGenerating}
              hasMessages={false}
              hasTopic={false}
              borderless
              interactionMode={editor.interactionMode}
              onModeChange={editor.setInteractionMode}
              fastTrack={editor.fastTrack}
              onFastTrackChange={editor.setFastTrack}
            />
          </div>
        </div>
      ) : (
        <>
          <ChatMessageList messages={editor.chatMessages} callbacks={callbacks} data={data} />

          {editor.activeProgress ? (
            <ProgressBar progress={editor.activeProgress} />
          ) : editor.isGenerating ? (
            <ProgressBar
              progress={{ node: "connecting", label: "파이프라인 연결 중...", percent: 0 }}
            />
          ) : null}

          <ChatInput
            onSend={editor.sendMessage}
            disabled={editor.isGenerating}
            hasMessages={editor.chatMessages.length > 1}
            hasTopic={!!editor.topic.trim()}
            interactionMode={editor.interactionMode}
            onModeChange={editor.setInteractionMode}
            fastTrack={editor.fastTrack}
            onFastTrackChange={editor.setFastTrack}
            isEditMode={isEditMode}
            onCancel={editor.cancelOperation}
          />
        </>
      )}
    </div>
  );
}
