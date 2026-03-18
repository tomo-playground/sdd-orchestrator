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
  chatResetToken: number;
  getMessages: (id: number | null) => ChatMessage[];
  saveMessages: (id: number | null, msgs: ChatMessage[]) => void;
  clearMessages: (id: number | null) => void;
  migrateFromTemp: (newId: number) => void;
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
  const {
    storyboardId,
    chatResetToken,
    getMessages,
    saveMessages,
    clearMessages,
    migrateFromTemp,
  } = deps;

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(() => {
    const saved = getMessages(storyboardId);
    return saved.length > 0 ? saved : [createWelcomeMessage()];
  });
  const chatMessagesRef = useRef(chatMessages);
  chatMessagesRef.current = chatMessages;

  const [activeProgress, setActiveProgress] = useState<ActiveProgress>(null);
  const topicRef = useRef<string>("");

  // 채팅 메시지 변경 시 store에 자동 저장 (typing indicator 제외, 500ms debounce)
  // storyboardId가 null이면 임시 key("__new__")에 저장하여 새로고침 시에도 보존
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => {
    const persistable = chatMessages.filter((m) => m.contentType !== "typing");
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
  // null → number 전환 시 임시 key 데이터를 새 id로 이관
  const prevStoryboardIdRef = useRef(storyboardId);
  const prevResetTokenRef = useRef(chatResetToken);
  useEffect(() => {
    const tokenChanged = prevResetTokenRef.current !== chatResetToken;
    prevResetTokenRef.current = chatResetToken;

    if (!tokenChanged && prevStoryboardIdRef.current === storyboardId) return;
    const prevId = prevStoryboardIdRef.current;
    prevStoryboardIdRef.current = storyboardId;

    // 새 영상(null) → 저장 완료(number) 전환: React state 메시지를 새 키로 직접 저장
    // debounce(500ms) 미완료 시 localStorage.__new__가 비어있을 수 있으므로
    // localStorage가 아닌 현재 React state를 SSOT로 사용
    if (prevId === null && storyboardId !== null) {
      const current = chatMessagesRef.current.filter((m) => m.contentType !== "typing");
      if (current.length > 0) {
        saveMessages(storyboardId, current);
      }
      migrateFromTemp(storyboardId);
      // 이미 React state에 메시지가 있으므로 리셋하지 않고 유지
      return;
    }

    const saved = getMessages(storyboardId);
    setChatMessages(saved.length > 0 ? saved : [createWelcomeMessage()]);
    setActiveProgress(null);
    topicRef.current = "";
  }, [storyboardId, chatResetToken, getMessages, saveMessages, migrateFromTemp]);

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
        contentType: "typing" as const,
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
