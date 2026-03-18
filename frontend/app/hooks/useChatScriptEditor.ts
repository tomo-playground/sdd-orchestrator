"use client";

import { useCallback, useEffect, useRef } from "react";
import { useContextStore } from "../store/useContextStore";
import { useUIStore } from "../store/useUIStore";
import { useChatStore } from "../store/useChatStore";
import { useScriptEditor } from "./useScriptEditor";
import { useSceneEditActions } from "./useSceneEditActions";
import { useChatMessages } from "./useChatMessages";
import { useStreamingPipeline } from "./useStreamingPipeline";
import { useTopicAnalysis } from "./useTopicAnalysis";
import type { ScriptEditorActions } from "./scriptEditor";
import { createReconstructedMessages } from "../utils/chatMessageFactory";
import type { ChatMessage, ActiveProgress, SettingsRecommendation } from "../types/chat";

export type ChatScriptEditorActions = ScriptEditorActions & {
  chatMessages: ChatMessage[];
  activeProgress: ActiveProgress;
  isAnalyzing: boolean;
  sendMessage: (text: string) => Promise<void>;
  applyAndGenerate: (rec: SettingsRecommendation) => void;
  confirmAndGenerate: () => void;
  clearChat: () => void;
  cancelOperation: () => void;
  setInteractionMode: (mode: "auto" | "guided" | "hands_on") => void;
  setFastTrack: (enabled: boolean) => void;
  applySceneEdits: () => void;
  rejectSceneEdit: () => void;
};

export function useChatScriptEditor(options?: {
  onSaved?: (id: number) => void;
}): ChatScriptEditorActions {
  const groupId = useContextStore((s) => s.groupId);
  const storyboardId = useContextStore((s) => s.storyboardId);
  const showToast = useUIStore((s) => s.showToast);
  const chatResetToken = useUIStore((s) => s.chatResetToken);
  const { getMessages, saveMessages, clearMessages, migrateFromTemp } = useChatStore();

  // ── 1. Chat messages state ──
  const {
    chatMessages,
    setChatMessages,
    chatMessagesRef,
    activeProgress,
    setActiveProgress,
    topicRef,
    addMessage,
    addTypingIndicator,
    removeTypingIndicator,
    clearChat: clearChatBase,
  } = useChatMessages({
    storyboardId,
    chatResetToken,
    getMessages,
    saveMessages,
    clearMessages,
    migrateFromTemp,
  });

  // ── 2. SSE → Chat event pipeline ──
  const editorRef = useRef<ScriptEditorActions | null>(null);
  const { onNodeEvent } = useStreamingPipeline({
    setChatMessages,
    setActiveProgress,
    addMessage,
    editorRef,
  });

  // ── 3. Script editor with onNodeEvent injected ──
  const editor = useScriptEditor({ onSaved: options?.onSaved, onNodeEvent });
  editorRef.current = editor;

  // ── 4. Scene edit actions ──
  const { handleEditRequest, applySceneEdits, rejectSceneEdit, isEditingRef } = useSceneEditActions(
    {
      editorRef,
      chatMessagesRef,
      topicRef,
      addMessage,
      setChatMessages,
      addTypingIndicator,
      removeTypingIndicator,
    }
  );

  // ── 5. Topic analysis + generation ──
  const { sendMessage, confirmAndGenerate, applyAndGenerate, cancelOperation, isAnalyzing } =
    useTopicAnalysis({
      groupId,
      editorRef,
      chatMessagesRef,
      topicRef,
      addMessage,
      addTypingIndicator,
      removeTypingIndicator,
      setActiveProgress,
      isEditingRef,
      handleEditRequest,
      showToast,
      editorCancel: editor.cancel,
    });

  // 씬 데이터는 있지만 채팅 히스토리가 유실된 경우 최소 대화 복원
  const reconstructedRef = useRef<number | null>(null);
  useEffect(() => {
    if (
      storyboardId &&
      reconstructedRef.current !== storyboardId &&
      editor.scenes.length > 0 &&
      chatMessages.length <= 1 &&
      editor.topic
    ) {
      reconstructedRef.current = storyboardId;
      setChatMessages(createReconstructedMessages(editor.topic, editor.scenes.length));
    }
  }, [storyboardId, editor.scenes.length, chatMessages.length, editor.topic, setChatMessages]);

  const clearChat = useCallback(() => {
    clearChatBase(() => editorRef.current?.reset());
  }, [clearChatBase]);

  const setInteractionMode = useCallback((mode: "auto" | "guided" | "hands_on") => {
    editorRef.current?.setField("interactionMode", mode);
  }, []);

  const setFastTrack = useCallback((enabled: boolean) => {
    editorRef.current?.setField("fastTrack", enabled);
  }, []);

  return {
    ...editor,
    chatMessages,
    activeProgress,
    isAnalyzing,
    sendMessage,
    applyAndGenerate,
    confirmAndGenerate,
    clearChat,
    cancelOperation,
    setInteractionMode,
    setFastTrack,
    applySceneEdits,
    rejectSceneEdit,
  };
}
