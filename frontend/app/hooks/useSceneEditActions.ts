"use client";

import { useCallback, useRef, type MutableRefObject } from "react";
import { API_BASE } from "../constants";
import type { ScriptEditorActions } from "./scriptEditor";
import type { ChatMessage, SceneEditResult } from "../types/chat";

function nextId() {
  return crypto.randomUUID();
}

function assistantMsg(text: string): ChatMessage {
  return { id: nextId(), role: "assistant", contentType: "assistant", text, timestamp: Date.now() };
}

type SceneEditDeps = {
  editorRef: MutableRefObject<ScriptEditorActions>;
  chatMessagesRef: MutableRefObject<ChatMessage[]>;
  topicRef: MutableRefObject<string>;
  addMessage: (msg: ChatMessage) => void;
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
};

export function useSceneEditActions(deps: SceneEditDeps) {
  const { editorRef, chatMessagesRef, topicRef, addMessage, setChatMessages } = deps;
  const isEditingRef = useRef(false);

  const handleEditRequest = useCallback(
    async (text: string) => {
      if (isEditingRef.current) return;
      isEditingRef.current = true;
      try {
        const scenes = editorRef.current.scenes.map((s) => ({
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
              language: editorRef.current.language,
              structure: editorRef.current.structure,
            },
          }),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        if (!data.edited_scenes?.length) {
          addMessage(assistantMsg("수정할 내용을 찾지 못했습니다."));
          return;
        }
        const editResult: SceneEditResult = {
          editedScenes: data.edited_scenes,
          reasoning: data.reasoning ?? "",
          unchangedCount: data.unchanged_count ?? 0,
        };
        addMessage({
          id: nextId(),
          role: "assistant",
          contentType: "scene_edit_diff",
          editResult,
          timestamp: Date.now(),
        });
      } catch (err) {
        console.error("[SceneEdit]", err);
        addMessage(assistantMsg("씬 수정 중 오류가 발생했습니다. 다시 시도해 주세요."));
      } finally {
        isEditingRef.current = false;
      }
    },
    [editorRef, topicRef, addMessage]
  );

  const applySceneEdits = useCallback(() => {
    const diffMsg = [...chatMessagesRef.current]
      .reverse()
      .find((m) => m.contentType === "scene_edit_diff" && !m.editApplied);
    if (!diffMsg?.editResult) return;
    for (const edited of diffMsg.editResult.editedScenes) {
      const patch: Record<string, unknown> = {};
      if (edited.script != null) patch.script = edited.script;
      if (edited.speaker != null) patch.speaker = edited.speaker;
      if (edited.duration != null) patch.duration = edited.duration;
      if (edited.image_prompt != null) patch.image_prompt = edited.image_prompt;
      if (edited.image_prompt_ko != null) patch.image_prompt_ko = edited.image_prompt_ko;
      const arrIdx = editorRef.current.scenes.findIndex((s) => s.order === edited.scene_index);
      if (arrIdx >= 0) editorRef.current.updateScene(arrIdx, patch);
    }
    editorRef.current.save();
    setChatMessages((prev) =>
      prev.map((m) => (m.id === diffMsg.id ? { ...m, editApplied: true } : m))
    );
    addMessage(assistantMsg("수정 사항이 적용되었습니다."));
  }, [editorRef, chatMessagesRef, setChatMessages, addMessage]);

  const rejectSceneEdit = useCallback(() => {
    addMessage(assistantMsg("수정을 취소했습니다."));
  }, [addMessage]);

  return { handleEditRequest, applySceneEdits, rejectSceneEdit, isEditingRef };
}
