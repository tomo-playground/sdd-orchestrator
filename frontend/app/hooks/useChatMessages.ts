"use client";

import {
  useState,
  useCallback,
  useRef,
  useEffect,
  type Dispatch,
  type SetStateAction,
  type MutableRefObject,
} from "react";
import type { ChatMessage, ActiveProgress } from "../types/chat";
import { createWelcomeMessage } from "../utils/chatMessageFactory";

type ChatMessagesDeps = {
  storyboardId: number | null;
  getMessages: (id: number | null) => ChatMessage[];
  saveMessages: (id: number | null, msgs: ChatMessage[]) => void;
  clearMessages: (id: number | null) => void;
};

export type ChatMessagesReturn = {
  chatMessages: ChatMessage[];
  setChatMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  chatMessagesRef: MutableRefObject<ChatMessage[]>;
  activeProgress: ActiveProgress;
  setActiveProgress: Dispatch<SetStateAction<ActiveProgress>>;
  topicRef: MutableRefObject<string>;
  addMessage: (msg: ChatMessage) => void;
  addTypingIndicator: (hint: string) => string;
  removeTypingIndicator: (id: string) => void;
  clearChat: (editorReset: () => void) => void;
};

export function useChatMessages(deps: ChatMessagesDeps): ChatMessagesReturn {
  const { storyboardId, getMessages, saveMessages, clearMessages } = deps;

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(() => {
    const saved = getMessages(storyboardId);
    return saved.length > 0 ? saved : [createWelcomeMessage()];
  });
  const chatMessagesRef = useRef(chatMessages);
  chatMessagesRef.current = chatMessages;

  const [activeProgress, setActiveProgress] = useState<ActiveProgress>(null);
  const topicRef = useRef<string>("");

  // 채팅 메시지 변경 시 store에 자동 저장 (typing indicator 제외, 500ms debounce)
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => {
    if (!storyboardId) return;
    const persistable = chatMessages.filter((m) => !m.id.startsWith("typing-"));
    if (persistable.length > 1) {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(() => {
        saveMessages(storyboardId, persistable);
      }, 500);
    }
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [chatMessages, storyboardId, saveMessages]);

  // 스토리보드 변경 시 해당 히스토리 복원
  const prevStoryboardIdRef = useRef(storyboardId);
  useEffect(() => {
    if (prevStoryboardIdRef.current === storyboardId) return;
    prevStoryboardIdRef.current = storyboardId;
    const saved = getMessages(storyboardId);
    setChatMessages(saved.length > 0 ? saved : [createWelcomeMessage()]);
    setActiveProgress(null);
    topicRef.current = "";
  }, [storyboardId, getMessages]);

  const addMessage = useCallback((msg: ChatMessage) => {
    setChatMessages((prev) => [...prev, msg]);
  }, []);

  const addTypingIndicator = useCallback((hint: string) => {
    const id = `typing-${Date.now()}`;
    setChatMessages((prev) => [
      ...prev,
      {
        id,
        role: "assistant" as const,
        contentType: "assistant" as const,
        text: hint,
        timestamp: Date.now(),
      },
    ]);
    return id;
  }, []);

  const removeTypingIndicator = useCallback((id: string) => {
    setChatMessages((prev) => prev.filter((m) => m.id !== id));
  }, []);

  const clearChat = useCallback(
    (editorReset: () => void) => {
      setChatMessages([createWelcomeMessage()]);
      setActiveProgress(null);
      topicRef.current = "";
      clearMessages(storyboardId);
      editorReset();
    },
    [storyboardId, clearMessages]
  );

  return {
    chatMessages,
    setChatMessages,
    chatMessagesRef,
    activeProgress,
    setActiveProgress,
    topicRef,
    addMessage,
    addTypingIndicator,
    removeTypingIndicator,
    clearChat,
  };
}
