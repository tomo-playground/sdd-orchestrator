"use client";

import { useState, useCallback, useRef } from "react";
import { API_BASE } from "../constants";
import { useContextStore } from "../store/useContextStore";
import { useUIStore } from "../store/useUIStore";
import { useScriptEditor } from "./useScriptEditor";
import { useSceneEditActions } from "./useSceneEditActions";
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
  setInteractionMode: (mode: "auto" | "guided" | "hands_on") => void;
  applySceneEdits: () => void;
  rejectSceneEdit: () => void;
};

const PIPELINE_NODES = new Set([
  "director_plan",
  "critic",
  "writer",
  "cinematographer",
  "director",
]);

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
  const chatMessagesRef = useRef(chatMessages);
  chatMessagesRef.current = chatMessages;
  const [activeProgress, setActiveProgress] = useState<ActiveProgress>(null);
  const isAnalyzingRef = useRef(false);
  const topicRef = useRef<string>("");

  const addMessage = useCallback((msg: ChatMessage) => {
    setChatMessages((prev) => [...prev, msg]);
  }, []);

  // ── SSE → Chat event callback (injected into useScriptEditor) ──
  const onNodeEvent = useCallback(
    (event: ScriptStreamEvent) => {
      // Pipeline step messages for major nodes
      if (event.status === "running" && PIPELINE_NODES.has(event.node) && event.node_result) {
        setChatMessages((prev) => {
          const existing = prev.findIndex(
            (m) => m.contentType === "pipeline_step" && m.nodeName === event.node
          );
          const msg: ChatMessage = {
            id: existing >= 0 ? prev[existing].id : nextId(),
            role: "assistant",
            contentType: "pipeline_step",
            nodeName: event.node,
            nodeResult: event.node_result as Record<string, unknown>,
            timestamp: Date.now(),
          };
          if (existing >= 0) {
            const next = [...prev];
            next[existing] = msg;
            return next;
          }
          return [...prev, msg];
        });
      }

      // Director plan gate
      if (
        event.status === "waiting_for_input" &&
        event.node === "director_plan_gate" &&
        event.result?.director_plan
      ) {
        setActiveProgress(null);
        addMessage({
          id: nextId(),
          role: "assistant",
          contentType: "plan_review_gate",
          text: "디렉터 플랜을 검토해주세요.",
          directorPlan: event.result.director_plan as Record<string, unknown>,
          skipStages: (event.result.skip_stages as string[]) ?? [],
          timestamp: Date.now(),
        });
        return;
      }

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
        // Auto-save triggers onSaved → setActiveTab("stage")
        setTimeout(() => editorRef.current.save(), 300);
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

  // ── Scene edit actions (extracted hook) ──
  const { handleEditRequest, applySceneEdits, rejectSceneEdit, isEditingRef } = useSceneEditActions(
    {
      editorRef,
      chatMessagesRef,
      topicRef,
      addMessage,
      setChatMessages,
    }
  );

  // ── 시리즈 이력 기본값으로 Gemini 호출 스킵 ──
  const tryGroupDefaults = useCallback(
    async (text: string): Promise<boolean> => {
      if (!groupId || topicRef.current) return false; // 첫 메시지만
      try {
        const res = await fetch(`${API_BASE}/groups/${groupId}/defaults`);
        if (!res.ok) return false;
        const defaults = await res.json();
        if (!defaults.has_history) return false;

        topicRef.current = text;
        editorRef.current.setField("topic", text);
        addMessage({
          id: nextId(),
          role: "assistant",
          contentType: "settings_recommend",
          text: "이전 에피소드 설정을 기반으로 추천합니다. 변경이 필요하면 드롭다운에서 수정하세요.",
          recommendation: {
            status: "recommend",
            resolved_topic: text,
            reasoning:
              "이전 에피소드 설정을 기반으로 추천합니다. 변경이 필요하면 드롭다운에서 수정하세요.",
            duration: defaults.duration,
            language: defaults.language,
            structure: defaults.structure,
            character_id: defaults.character_id,
            character_name: defaults.character_name,
            character_b_id: defaults.character_b_id ?? null,
            character_b_name: defaults.character_b_name ?? null,
            available_options: defaults.available_options,
          },
          timestamp: Date.now(),
        });
        return true;
      } catch {
        return false;
      }
    },
    [groupId, addMessage]
  );

  // ── Topic analysis via API (대화형 핑퐁 지원) ──
  const sendMessage = useCallback(
    async (text: string) => {
      if (isAnalyzingRef.current || isEditingRef.current) return;
      addMessage({ id: nextId(), role: "user", contentType: "user", text, timestamp: Date.now() });

      // Post-completion: 씬이 있으면 편집 모드로 전환
      const hasCompletion = chatMessagesRef.current.some((m) => m.contentType === "completion");
      if (hasCompletion && editorRef.current.scenes.length > 0) {
        await handleEditRequest(text);
        return;
      }

      // P1: 시리즈 이력이 있으면 Gemini 호출 스킵
      isAnalyzingRef.current = true;
      try {
        const usedDefaults = await tryGroupDefaults(text);
        if (usedDefaults) return;

        // 첫 user 메시지에서 초기 topic 설정
        if (!topicRef.current) {
          topicRef.current = text;
          editorRef.current.setField("topic", text);
        }

        // 대화 이력 구성 (user + assistant text)
        const history = chatMessagesRef.current
          .filter(
            (m) =>
              (m.role === "user" && m.contentType === "user") ||
              (m.role === "assistant" &&
                (m.contentType === "clarification" || m.contentType === "settings_recommend"))
          )
          .map((m) => {
            let msgText = m.text || "";
            if (m.questions?.length) msgText += "\n" + m.questions.map((q) => `• ${q}`).join("\n");
            return { role: m.role, text: msgText };
          });
        history.push({ role: "user", text });
        const trimmedHistory = history.slice(-20);

        const res = await fetch(`${API_BASE}/scripts/analyze-topic`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            topic: topicRef.current || text,
            description: editorRef.current.description || undefined,
            group_id: groupId,
            messages: trimmedHistory,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: SettingsRecommendation = await res.json();

        if (data.resolved_topic) {
          topicRef.current = data.resolved_topic;
          editorRef.current.setField("topic", data.resolved_topic);
        }

        if (data.status === "clarify") {
          addMessage({
            id: nextId(),
            role: "assistant",
            contentType: "clarification",
            text: data.reasoning,
            questions: data.questions,
            timestamp: Date.now(),
          });
        } else {
          addMessage({
            id: nextId(),
            role: "assistant",
            contentType: "settings_recommend",
            text: data.reasoning,
            recommendation: data,
            timestamp: Date.now(),
          });
        }
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
    [groupId, addMessage, handleEditRequest, isEditingRef, tryGroupDefaults]
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
    // character_b: 항상 명시적으로 설정 (Monologue 전환 시 null로 정리)
    editorRef.current.setField("characterBId", rec.character_b_id);
    editorRef.current.setField("characterBName", rec.character_b_name);
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
    topicRef.current = "";
    editorRef.current.reset();
  }, []);

  const setInteractionMode = useCallback((mode: "auto" | "guided" | "hands_on") => {
    editorRef.current.setField("interactionMode", mode);
  }, []);

  return {
    ...editor,
    chatMessages,
    activeProgress,
    sendMessage,
    applyAndGenerate,
    confirmAndGenerate,
    clearChat,
    setInteractionMode,
    applySceneEdits,
    rejectSceneEdit,
  };
}
