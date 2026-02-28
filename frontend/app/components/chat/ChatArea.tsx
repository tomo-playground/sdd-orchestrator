"use client";

import { useCallback, useMemo } from "react";
import ChatMessageList from "./ChatMessageList";
import ChatInput from "./ChatInput";
import ProgressBar from "./ProgressBar";
import ModeChips from "./ModeChips";
import { useUIStore, type StudioTab } from "../../store/useUIStore";
import type { ChatScriptEditorActions } from "../../hooks/useChatScriptEditor";
import type { ChatMessageCallbacks, ChatMessageData } from "./ChatMessage";
import type { ScriptMode } from "./ModeChips";

type Props = {
  editor: ChatScriptEditorActions;
  currentMode: ScriptMode;
  onPresetChange: (preset: string, skipStages: string[]) => void;
};

export default function ChatArea({ editor, currentMode, onPresetChange }: Props) {
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
    }),
    [editor.applyAndGenerate, editor.resume, editor.confirmAndGenerate, handleNavigate]
  );

  const data: ChatMessageData = useMemo(
    () => ({
      scenes: editor.scenes,
      feedbackPresets: editor.feedbackPresets,
    }),
    [editor.scenes, editor.feedbackPresets]
  );

  const isInitialState = editor.chatMessages.length <= 1;

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
          <div className="mb-4 w-full max-w-xs">
            <ModeChips currentMode={currentMode} onPresetChange={onPresetChange} />
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
          />
        </>
      )}
    </div>
  );
}
