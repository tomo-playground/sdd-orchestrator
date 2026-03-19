import type {
  AssistantMessage,
  UserMessage,
  ErrorMessage,
  CompletionMessage,
  CompletionMeta,
  CompletionSceneSummary,
  ChatMessage,
} from "../types/chat";

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

/**
 * 씬 데이터는 있지만 채팅 히스토리가 유실된 경우, 최소한의 대화를 복원한다.
 * (localStorage 초과/삭제 등으로 히스토리가 사라진 경우 대비)
 */
export function createReconstructedMessages(topic: string, sceneCount: number): ChatMessage[] {
  const now = Date.now();
  return [
    createWelcomeMessage(),
    {
      id: `recon-user-${now}`,
      role: "user" as const,
      contentType: "user" as const,
      text: topic,
      timestamp: now - 2,
    },
    {
      id: `recon-completion-${now}`,
      role: "assistant" as const,
      contentType: "completion" as const,
      text: `대본이 생성되었습니다. (${sceneCount}개 씬)\n\n씬을 수정하려면 메시지를 보내주세요.`,
      timestamp: now - 1,
    } satisfies CompletionMessage,
  ];
}

/** 스크립트 생성 완료 시 CompletionCard에 표시할 메타 데이터를 구성한다. */
export function buildCompletionMeta(
  scenes: Array<{
    order?: number;
    speaker?: string;
    duration?: number;
    script?: string;
    context_tags?: Record<string, unknown>;
  }>,
  editor: {
    topic?: string;
    structure?: string;
    characterName?: string | null;
    characterBName?: string | null;
  } | null
): CompletionMeta {
  const summaries: CompletionSceneSummary[] = scenes.map((s, i) => ({
    order: s.order ?? i,
    speaker: s.speaker ?? "A",
    duration: s.duration ?? 3,
    scriptPreview: (s.script ?? "").slice(0, 30),
    emotion: (s.context_tags?.emotion as string) ?? undefined,
  }));
  return {
    topic: editor?.topic ?? "",
    structure: editor?.structure ?? "monologue",
    totalDuration: summaries.reduce((sum, s) => sum + s.duration, 0),
    characterAName: editor?.characterName ?? null,
    characterBName: editor?.characterBName ?? null,
    sceneSummaries: summaries,
  };
}
