import type { AssistantMessage, UserMessage, ErrorMessage, ChatMessage } from "../types/chat";

export function createMessageId(): string {
  return crypto.randomUUID();
}

export function createAssistantMessage(text: string): AssistantMessage {
  return {
    id: createMessageId(),
    role: "assistant",
    contentType: "assistant",
    text,
    timestamp: Date.now(),
  };
}

export function createUserMessage(text: string): UserMessage {
  return {
    id: createMessageId(),
    role: "user",
    contentType: "user",
    text,
    timestamp: Date.now(),
  };
}

export function createErrorMessage(text: string, errorMessage: string): ErrorMessage {
  return {
    id: createMessageId(),
    role: "assistant",
    contentType: "error",
    text,
    errorMessage,
    timestamp: Date.now(),
  };
}

export function createWelcomeMessage(): ChatMessage {
  return {
    id: "welcome",
    role: "assistant",
    contentType: "assistant",
    text: "주제를 입력하면 AI가 최적의 설정을 추천해 드립니다.",
    timestamp: Date.now(),
  };
}
