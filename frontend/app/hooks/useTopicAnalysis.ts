"use client";

import {
  useCallback,
  useRef,
  useEffect,
  type MutableRefObject,
  type Dispatch,
  type SetStateAction,
} from "react";
import { API_BASE } from "../constants";
import type { ScriptEditorActions } from "./scriptEditor";
import type { ChatMessage, ActiveProgress, SettingsRecommendation } from "../types/chat";
import {
  createMessageId,
  createAssistantMessage,
  createUserMessage,
} from "../utils/chatMessageFactory";
import { ensureDraftStoryboard } from "../store/actions/draftActions";

/** chatMessages에서 user/clarification/settings_recommend만 추출하여 {role, text} 배열로 변환 */
function buildChatHistory(messages: ChatMessage[]): Array<{ role: string; text: string }> {
  return messages
    .filter(
      (m) =>
        m.contentType === "user" ||
        m.contentType === "clarification" ||
        m.contentType === "settings_recommend"
    )
    .map((m) => {
      let msgText = "text" in m ? m.text || "" : "";
      if (m.contentType === "clarification" && m.questions?.length) {
        msgText += "\n" + m.questions.map((q: string) => `• ${q}`).join("\n");
      }
      return { role: m.role, text: msgText };
    })
    .slice(-20);
}

type TopicAnalysisDeps = {
  groupId: number | null;
  editorRef: MutableRefObject<ScriptEditorActions | null>;
  chatMessagesRef: MutableRefObject<ChatMessage[]>;
  topicRef: MutableRefObject<string>;
  addMessage: (msg: ChatMessage) => void;
  addTypingIndicator: (hint: string) => string;
  removeTypingIndicator: (id: string) => void;
  setActiveProgress: Dispatch<SetStateAction<ActiveProgress>>;
  isEditingRef: MutableRefObject<boolean>;
  handleEditRequest: (text: string) => Promise<void>;
  showToast: (msg: string, type: "success" | "error" | "warning") => void;
  editorCancel: () => void;
};

export function useTopicAnalysis(deps: TopicAnalysisDeps) {
  const {
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
    editorCancel,
  } = deps;

  const isAnalyzingRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  // 언마운트 시 진행 중 요청 취소
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // ── Topic analysis via API (대화형 핑퐁 지원) ──
  const sendMessage = useCallback(
    async (text: string) => {
      if (isAnalyzingRef.current || isEditingRef.current) return;
      addMessage(createUserMessage(text));

      // Post-completion: 씬이 있으면 편집 모드로 전환
      const hasCompletion = chatMessagesRef.current.some((m) => m.contentType === "completion");
      if (hasCompletion && (editorRef.current?.scenes.length ?? 0) > 0) {
        await handleEditRequest(text);
        return;
      }

      isAnalyzingRef.current = true;
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const typingId = addTypingIndicator("분석 중...");
      try {
        // Draft storyboard 확보 (첫 호출 시 생성, 이후 기존 ID 반환)
        const draftId = await ensureDraftStoryboard();

        // 첫 user 메시지에서 초기 topic + description 설정
        if (!topicRef.current) {
          topicRef.current = text;
          editorRef.current?.setField("topic", text);
          if (!editorRef.current?.description) {
            editorRef.current?.setField("description", text);
          }
        }

        // 대화 이력 구성 (user + assistant text)
        const history = buildChatHistory(chatMessagesRef.current);
        history.push({ role: "user", text });
        const trimmedHistory = history.slice(-20);

        const res = await fetch(`${API_BASE}/scripts/analyze-topic`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          body: JSON.stringify({
            topic: topicRef.current || text,
            description: editorRef.current?.description || undefined,
            group_id: groupId,
            storyboard_id: draftId ?? undefined,
            messages: trimmedHistory,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: SettingsRecommendation = await res.json();

        removeTypingIndicator(typingId);

        if (data.resolved_topic) {
          topicRef.current = data.resolved_topic;
          editorRef.current?.setField("topic", data.resolved_topic);
        }

        if (data.status === "clarify") {
          addMessage({
            id: createMessageId(),
            role: "assistant",
            contentType: "clarification",
            text: data.reasoning,
            questions: data.questions,
            timestamp: Date.now(),
          });
        } else {
          addMessage({
            id: createMessageId(),
            role: "assistant",
            contentType: "settings_recommend",
            text: data.reasoning,
            recommendation: data,
            timestamp: Date.now(),
          });
        }
      } catch (err) {
        removeTypingIndicator(typingId);
        // AbortController.abort() 호출 시 무시
        if (err instanceof DOMException && err.name === "AbortError") return;
        addMessage({
          id: createMessageId(),
          role: "assistant",
          contentType: "error",
          text: "토픽 분석 중 오류가 발생했습니다.",
          errorMessage: "다시 시도하거나, 직접 설정을 조정해 주세요.",
          timestamp: Date.now(),
        });
      } finally {
        isAnalyzingRef.current = false;
        abortRef.current = null;
      }
    },
    [
      groupId,
      addMessage,
      addTypingIndicator,
      removeTypingIndicator,
      handleEditRequest,
      isEditingRef,
      chatMessagesRef,
      editorRef,
      topicRef,
    ]
  );

  // ── Apply recommendation fields to editor state ──
  const applyFields = useCallback(
    (rec: SettingsRecommendation) => {
      if (!editorRef.current) return;
      editorRef.current.setField("duration", rec.duration);
      editorRef.current.setField("language", rec.language);
      // structure도 반영 — Director가 캐릭터 없이도 올바른 구조로 진행하도록
      if (rec.structure) {
        editorRef.current.setField("structure", rec.structure);
      }
    },
    [editorRef]
  );

  /** chatMessages에서 대화 컨텍스트를 추출하여 editor에 설정 */
  const syncChatContext = useCallback(() => {
    editorRef.current?.setField("chatContext", buildChatHistory(chatMessagesRef.current));
  }, [editorRef, chatMessagesRef]);

  const confirmAndGenerate = useCallback(() => {
    if (!editorRef.current?.topic.trim()) {
      showToast("토픽을 입력해주세요", "warning");
      return;
    }
    syncChatContext();
    addMessage(createAssistantMessage("스크립트를 생성하고 있습니다..."));
    editorRef.current.generate();
  }, [editorRef, addMessage, showToast, syncChatContext]);

  const applyAndGenerate = useCallback(
    (rec: SettingsRecommendation) => {
      applyFields(rec);
      syncChatContext();
      addMessage(createAssistantMessage("설정을 반영하고 스크립트를 생성합니다..."));
      // setTimeout: React 배치 업데이트 → 렌더 → stateRef 갱신 후 generate 실행
      setTimeout(() => editorRef.current?.generate(), 0);
    },
    [applyFields, addMessage, syncChatContext, editorRef]
  );

  const cancelOperation = useCallback(() => {
    abortRef.current?.abort();
    editorCancel();
    setActiveProgress(null);
    addMessage(createAssistantMessage("생성이 취소되었습니다."));
  }, [editorCancel, setActiveProgress, addMessage]);

  return {
    sendMessage,
    confirmAndGenerate,
    applyAndGenerate,
    cancelOperation,
    isAnalyzingRef,
  };
}
