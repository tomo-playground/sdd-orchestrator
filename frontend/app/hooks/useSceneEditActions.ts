"use client";

import { useCallback, useRef, type MutableRefObject } from "react";
import { API_BASE } from "../constants";
import type { ScriptEditorActions } from "./scriptEditor";
import type { ChatMessage, SceneEditDiffMessage, SceneEditResult } from "../types/chat";
import { createMessageId, createAssistantMessage } from "../utils/chatMessageFactory";

type SceneEditDeps = {
  editorRef: MutableRefObject<ScriptEditorActions | null>;
  chatMessagesRef: MutableRefObject<ChatMessage[]>;
  topicRef: MutableRefObject<string>;
  addMessage: (msg: ChatMessage) => void;
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  addTypingIndicator: (hint: string) => string;
  removeTypingIndicator: (id: string) => void;
};

export function useSceneEditActions(deps: SceneEditDeps) {
  const {
    editorRef,
    chatMessagesRef,
    topicRef,
    addMessage,
    setChatMessages,
    addTypingIndicator,
    removeTypingIndicator,
  } = deps;
  const isEditingRef = useRef(false);

  const handleEditRequest = useCallback(
    async (text: string) => {
      if (isEditingRef.current || !editorRef.current) return;
      isEditingRef.current = true;
      const editor = editorRef.current;
      const typingId = addTypingIndicator("수정 사항 분석 중...");
      try {
        const scenes = editor.scenes.map((s) => ({
          scene_index: s.order,
          script: s.script,
          speaker: s.speaker,
          duration: s.duration,
          image_prompt: s.image_prompt,
          image_prompt_ko: s.image_prompt_ko,
        }));
        const res = await fetch(`${API_BASE}/scripts/edit-scenes`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            instruction: text,
            scenes,
            context: {
              topic: topicRef.current,
              language: editor.language,
              structure: editor.structure,
            },
          }),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        removeTypingIndicator(typingId);
        if (!data.edited_scenes?.length) {
          addMessage(createAssistantMessage("수정할 내용을 찾지 못했습니다."));
          return;
        }
        const editResult: SceneEditResult = {
          editedScenes: data.edited_scenes,
          reasoning: data.reasoning ?? "",
          unchangedCount: data.unchanged_count ?? 0,
        };
        addMessage({
          id: createMessageId(),
          role: "assistant",
          contentType: "scene_edit_diff",
          editResult,
          timestamp: Date.now(),
        });
      } catch (err) {
        removeTypingIndicator(typingId);
        console.error("[SceneEdit]", err);
        addMessage(createAssistantMessage("씬 수정 중 오류가 발생했습니다. 다시 시도해 주세요."));
      } finally {
        isEditingRef.current = false;
      }
    },
    [editorRef, topicRef, addMessage, addTypingIndicator, removeTypingIndicator]
  );

  const applySceneEdits = useCallback(() => {
    const diffMsg = [...chatMessagesRef.current]
      .reverse()
      .find(
        (m): m is SceneEditDiffMessage => m.contentType === "scene_edit_diff" && !m.editApplied
      );
    if (!diffMsg || !editorRef.current) return;
    const editor = editorRef.current;
    for (const edited of diffMsg.editResult.editedScenes) {
      const patch: Record<string, unknown> = {};
      if (edited.script != null) patch.script = edited.script;
      if (edited.speaker != null) patch.speaker = edited.speaker;
      if (edited.duration != null) patch.duration = edited.duration;
      if (edited.image_prompt != null) patch.image_prompt = edited.image_prompt;
      if (edited.image_prompt_ko != null) patch.image_prompt_ko = edited.image_prompt_ko;
      const arrIdx = editor.scenes.findIndex((s) => s.order === edited.scene_index);
      if (arrIdx >= 0) editor.updateScene(arrIdx, patch);
    }
    editor.save();
    setChatMessages((prev) =>
      prev.map((m) => (m.id === diffMsg.id ? { ...m, editApplied: true } : m))
    );
    addMessage(createAssistantMessage("수정 사항이 적용되었습니다."));
  }, [editorRef, chatMessagesRef, setChatMessages, addMessage]);

  const rejectSceneEdit = useCallback(() => {
    addMessage(createAssistantMessage("수정을 취소했습니다."));
  }, [addMessage]);

  return { handleEditRequest, applySceneEdits, rejectSceneEdit, isEditingRef };
}
