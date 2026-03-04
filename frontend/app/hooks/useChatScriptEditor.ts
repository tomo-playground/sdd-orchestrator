"use client";

import { useCallback, useRef } from "react";
import { useContextStore } from "../store/useContextStore";
import { useUIStore } from "../store/useUIStore";
import { useChatStore } from "../store/useChatStore";
import { useScriptEditor } from "./useScriptEditor";
import { useSceneEditActions } from "./useSceneEditActions";
import { useChatMessages } from "./useChatMessages";
import { useStreamingPipeline } from "./useStreamingPipeline";
import { useTopicAnalysis } from "./useTopicAnalysis";
import type { ScriptEditorActions } from "./scriptEditor";
import type { ChatMessage, ActiveProgress, SettingsRecommendation } from "../types/chat";

export type ChatScriptEditorActions = ScriptEditorActions & {
  chatMessages: ChatMessage[];
  activeProgress: ActiveProgress;
  sendMessage: (text: string) => Promise<void>;
  applyAndGenerate: (rec: SettingsRecommendation) => void;
  confirmAndGenerate: () => void;
  clearChat: () => void;
  cancelOperation: () => void;
  setInteractionMode: (mode: "auto" | "guided" | "hands_on") => void;
  applySceneEdits: () => void;
  rejectSceneEdit: () => void;
};

export function useChatScriptEditor(options?: {
  onSaved?: (id: number) => void;
}): ChatScriptEditorActions {
  const groupId = useContextStore((s) => s.groupId);
  const storyboardId = useContextStore((s) => s.storyboardId);
  const showToast = useUIStore((s) => s.showToast);
  const { getMessages, saveMessages, clearMessages } = useChatStore();

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
  } = useChatMessages({ storyboardId, getMessages, saveMessages, clearMessages });

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
  const { sendMessage, confirmAndGenerate, applyAndGenerate, cancelOperation } = useTopicAnalysis({
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

  const clearChat = useCallback(() => {
    clearChatBase(() => editorRef.current?.reset());
  }, [clearChatBase]);

  const setInteractionMode = useCallback((mode: "auto" | "guided" | "hands_on") => {
    editorRef.current?.setField("interactionMode", mode);
  }, []);

  return {
    ...editor,
    chatMessages,
    activeProgress,
    sendMessage,
    applyAndGenerate,
    confirmAndGenerate,
    clearChat,
    cancelOperation,
    setInteractionMode,
    applySceneEdits,
    rejectSceneEdit,
  };
}
