"use client";

import { useState, useCallback, useRef } from "react";
import { API_BASE } from "../constants";
import { useContextStore } from "../store/useContextStore";
import { useUIStore } from "../store/useUIStore";
import { useScriptEditor } from "./useScriptEditor";
import type { ScriptEditorActions } from "./scriptEditor";
import type { ScriptStreamEvent } from "../types";
import type { ChatMessage, ActiveProgress, SettingsRecommendation } from "../types/chat";

function nextId() {
  return crypto.randomUUID();
}

function assistantMsg(text: string): ChatMessage {
  return { id: nextId(), role: "assistant", contentType: "assistant", text, timestamp: Date.now() };
}

export type ChatScriptEditorActions = ScriptEditorActions & {
  chatMessages: ChatMessage[];
  activeProgress: ActiveProgress;
  sendMessage: (text: string) => Promise<void>;
  applyAndGenerate: (rec: SettingsRecommendation) => void;
  confirmAndGenerate: () => void;
  clearChat: () => void;
};

function createWelcomeMessage(): ChatMessage {
  return {
    id: "welcome",
    role: "assistant",
    contentType: "assistant",
    text: "주제를 입력하면 AI가 최적의 설정을 추천해 드립니다.",
    timestamp: Date.now(),
  };
}

export function useChatScriptEditor(options?: {
  onSaved?: (id: number) => void;
}): ChatScriptEditorActions {
  const groupId = useContextStore((s) => s.groupId);
  const showToast = useUIStore((s) => s.showToast);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([createWelcomeMessage()]);
  const [activeProgress, setActiveProgress] = useState<ActiveProgress>(null);
  const isAnalyzingRef = useRef(false);

  const addMessage = useCallback((msg: ChatMessage) => {
    setChatMessages((prev) => [...prev, msg]);
  }, []);

  // ── SSE → Chat event callback (injected into useScriptEditor) ──
  const onNodeEvent = useCallback(
    (event: ScriptStreamEvent) => {
      if (event.status === "running") {
        setActiveProgress({ node: event.node, label: event.label, percent: event.percent });
        return;
      }

      // Concept gate
      if (
        event.status === "waiting_for_input" &&
        event.node === "concept_gate" &&
        event.result?.candidates
      ) {
        setActiveProgress(null);
        addMessage({
          id: nextId(),
          role: "assistant",
          contentType: "concept_gate",
          text: "컨셉을 선택해주세요.",
          concepts: event.result.candidates,
          recommendedConceptId: 0,
          timestamp: Date.now(),
        });
        return;
      }

      // Human gate (review)
      if (event.status === "waiting_for_input") {
        setActiveProgress(null);
        addMessage({
          id: nextId(),
          role: "assistant",
          contentType: "review_gate",
          text: "대본을 검토하고 승인하거나 수정 요청을 해주세요.",
          reviewResult: event.result?.review_result,
          productionSnapshot: event.result?.production_snapshot ?? null,
          timestamp: Date.now(),
        });
        return;
      }

      // Completed
      if (event.status === "completed" && event.result?.scenes) {
        setActiveProgress(null);
        addMessage({
          id: nextId(),
          role: "assistant",
          contentType: "completion",
          text: `스크립트 생성 완료! ${event.result.scenes.length}개 씬이 생성되었습니다.`,
          timestamp: Date.now(),
        });
        return;
      }

      // Error
      if (event.status === "error") {
        setActiveProgress(null);
        addMessage({
          id: nextId(),
          role: "assistant",
          contentType: "error",
          text: "생성 중 오류가 발생했습니다.",
          errorMessage: event.error ?? "Unknown error",
          timestamp: Date.now(),
        });
      }
    },
    [addMessage]
  );

  // useScriptEditor with onNodeEvent injected
  const editor = useScriptEditor({ onSaved: options?.onSaved, onNodeEvent });
  const editorRef = useRef(editor);
  editorRef.current = editor;

  // ── Topic analysis via API ──
  // editorRef를 통해 최신 editor 상태에 접근 (stale closure 방지)
  const sendMessage = useCallback(
    async (text: string) => {
      if (isAnalyzingRef.current) return;
      addMessage({ id: nextId(), role: "user", contentType: "user", text, timestamp: Date.now() });
      editorRef.current.setField("topic", text);

      isAnalyzingRef.current = true;
      try {
        const res = await fetch(`${API_BASE}/scripts/analyze-topic`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            topic: text,
            description: editorRef.current.description || undefined,
            group_id: groupId,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: SettingsRecommendation = await res.json();

        addMessage({
          id: nextId(),
          role: "assistant",
          contentType: "settings_recommend",
          text: data.reasoning,
          recommendation: data,
          timestamp: Date.now(),
        });
      } catch {
        addMessage({
          id: nextId(),
          role: "assistant",
          contentType: "error",
          text: "토픽 분석 중 오류가 발생했습니다.",
          errorMessage: "다시 시도하거나, 직접 설정을 조정해 주세요.",
          timestamp: Date.now(),
        });
      } finally {
        isAnalyzingRef.current = false;
      }
    },
    [groupId, addMessage]
  );

  // ── Apply recommendation fields to editor state (shared helper, refs-only → stable) ──
  const applyFields = useCallback((rec: SettingsRecommendation) => {
    editorRef.current.setField("duration", rec.duration);
    editorRef.current.setField("language", rec.language);
    editorRef.current.setField("structure", rec.structure);
    if (rec.character_id != null) {
      editorRef.current.setField("characterId", rec.character_id);
      editorRef.current.setField("characterName", rec.character_name);
    }
    if (rec.character_b_id != null) {
      editorRef.current.setField("characterBId", rec.character_b_id);
      editorRef.current.setField("characterBName", rec.character_b_name);
    }
  }, []);

  // ── Generate — just delegates to editor.generate(), SSE flows via onNodeEvent ──
  // editor.generate()는 매 렌더마다 새 참조가 생성되므로 ref를 통해 안정적으로 접근
  const confirmAndGenerate = useCallback(() => {
    if (!editorRef.current.topic.trim()) {
      showToast("토픽을 입력해주세요", "warning");
      return;
    }
    addMessage(assistantMsg("스크립트를 생성하고 있습니다..."));
    editorRef.current.generate();
  }, [addMessage, showToast]);

  const applyAndGenerate = useCallback(
    (rec: SettingsRecommendation) => {
      applyFields(rec);
      addMessage(assistantMsg("설정을 반영하고 스크립트를 생성합니다..."));
      editorRef.current.generate();
    },
    [applyFields, addMessage]
  );

  const clearChat = useCallback(() => {
    setChatMessages([createWelcomeMessage()]);
    setActiveProgress(null);
    editorRef.current.reset();
  }, []);

  return {
    ...editor,
    chatMessages,
    activeProgress,
    sendMessage,
    applyAndGenerate,
    confirmAndGenerate,
    clearChat,
  };
}
