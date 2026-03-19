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

  /** 채팅 상태 초기화: 메시지 교체 + progress/topic 리셋 */
  const resetChatState = useCallback(
    (msgs: ChatMessage[]) => {
      setChatMessages(msgs);
      setActiveProgress(null);
      topicRef.current = "";
    },
    [setChatMessages]
  );

  // 스토리보드 변경 시 해당 히스토리 복원
  // null → number: (A) 새 영상 첫 저장 → 임시 키 이관, (B) 기존 영상 로드 → 히스토리 복원
  const prevStoryboardIdRef = useRef(storyboardId);
  const prevResetTokenRef = useRef(chatResetToken);
  useEffect(() => {
    const tokenChanged = prevResetTokenRef.current !== chatResetToken;
    prevResetTokenRef.current = chatResetToken;

    if (!tokenChanged && prevStoryboardIdRef.current === storyboardId) return;
    const prevId = prevStoryboardIdRef.current;
    prevStoryboardIdRef.current = storyboardId;

    // null → number 전환: 두 가지 시나리오 구분
    // (A) 새 영상 생성 후 첫 저장 → React state를 새 키로 이관 (대화 유지)
    // (B) 페이지 로드 (?id=X) → storyboardId가 null(초기값) → X로 변경 → 기존 히스토리 복원
    if (prevId === null && storyboardId !== null) {
      const existingSaved = getMessages(storyboardId);
      if (existingSaved.length > 0) {
        // (B) 이미 저장된 히스토리가 있음 → 기존 대화 복원 (덮어쓰기 금지)
        resetChatState(existingSaved);
        migrateFromTemp(storyboardId); // 고아 __new__ 키 정리
        return;
      }
      // (A) 새 영상: debounce 미완료 시 localStorage.__new__가 비어있을 수 있으므로
      // React state를 SSOT로 사용하여 새 키에 저장
      const current = chatMessagesRef.current.filter((m) => m.contentType !== "typing");
      if (current.length > 0) {
        saveMessages(storyboardId, current);
      }
      migrateFromTemp(storyboardId);
      // 이미 React state에 메시지가 있으므로 리셋하지 않고 유지
      return;
    }

    const saved = getMessages(storyboardId);
    resetChatState(saved.length > 0 ? saved : [createWelcomeMessage()]);
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
      resetChatState([createWelcomeMessage()]);
      clearMessages(storyboardId);
      editorReset();
    },
    [storyboardId, clearMessages, resetChatState]
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
