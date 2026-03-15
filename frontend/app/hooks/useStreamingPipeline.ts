"use client";

import { useCallback, type Dispatch, type SetStateAction, type MutableRefObject } from "react";
import type { ScriptEditorActions } from "./scriptEditor";
import type { ScriptStreamEvent, ConceptCandidate } from "../types";
import type { ChatMessage, ActiveProgress } from "../types/chat";
import { createMessageId } from "../utils/chatMessageFactory";

const PIPELINE_NODES = new Set([
  "director_plan",
  "research",
  "critic",
  "writer",
  "review",
  "revise",
  "cinematographer",
  "tts_designer",
  "sound_designer",
  "copyright_reviewer",
  "director",
  "explain",
]);

type StreamingPipelineDeps = {
  setChatMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  setActiveProgress: Dispatch<SetStateAction<ActiveProgress>>;
  addMessage: (msg: ChatMessage) => void;
  editorRef: MutableRefObject<ScriptEditorActions | null>;
};

export function useStreamingPipeline(deps: StreamingPipelineDeps) {
  const { setChatMessages, setActiveProgress, addMessage, editorRef } = deps;

  const onNodeEvent = useCallback(
    (event: ScriptStreamEvent) => {
      // Pipeline step messages for major nodes
      if (event.status === "running" && PIPELINE_NODES.has(event.node) && event.node_result) {
        setChatMessages((prev) => {
          const existing = prev.findIndex(
            (m) => m.contentType === "pipeline_step" && m.nodeName === event.node
          );
          const msg: ChatMessage = {
            id: existing >= 0 ? prev[existing].id : createMessageId(),
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
          id: createMessageId(),
          role: "assistant",
          contentType: "plan_review_gate",
          text: "디렉터 플랜을 검토해주세요.",
          topic: editorRef.current?.topic?.trim() || undefined,
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
        const candidates = event.result.candidates as ConceptCandidate[];
        const selectedConcept = event.result.selected_concept as ConceptCandidate | undefined;
        const recommendedConceptId = selectedConcept
          ? candidates.findIndex((c) => c.agent_role === selectedConcept.agent_role)
          : 0;
        addMessage({
          id: createMessageId(),
          role: "assistant",
          contentType: "concept_gate",
          text: "컨셉을 선택해주세요.",
          concepts: candidates,
          recommendedConceptId: recommendedConceptId >= 0 ? recommendedConceptId : 0,
          timestamp: Date.now(),
        });
        return;
      }

      // Human gate (review)
      if (event.status === "waiting_for_input") {
        setActiveProgress(null);
        addMessage({
          id: createMessageId(),
          role: "assistant",
          contentType: "review_gate",
          text: "대본을 검토하고 승인하거나 수정 요청을 해주세요.",
          reviewResult: event.result?.review_result,
          productionSnapshot: event.result?.production_snapshot ?? null,
          timestamp: Date.now(),
        });
        return;
      }

      // Completed — chat message only; save is handled by handleStreamOutcome
      // (onNodeEvent fires during processSSEStream, before scenes are committed)
      if (event.status === "completed" && event.result?.scenes) {
        setActiveProgress(null);
        addMessage({
          id: createMessageId(),
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
          id: createMessageId(),
          role: "assistant",
          contentType: "error",
          text: "생성 중 오류가 발생했습니다.",
          errorMessage: event.error ?? "Unknown error",
          timestamp: Date.now(),
        });
      }
    },
    [setChatMessages, setActiveProgress, addMessage, editorRef]
  );

  return { onNodeEvent };
}
