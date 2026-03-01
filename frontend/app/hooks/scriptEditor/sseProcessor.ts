import type React from "react";
import type { ScriptStreamEvent } from "../../types";
import { useRenderStore } from "../../store/useRenderStore";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { updatePipelineSteps, applyDirectorPlan } from "../../utils/pipelineSteps";
import { mapEventScenes } from "./mappers";
import type { SceneItem, ScriptEditorState } from "./types";

function friendlyErrorMessage(raw: string): string {
  if (raw.includes("500")) return "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
  if (raw.includes("429")) return "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.";
  // "stream" 단독 매칭 제거 — SSE 데이터에 "stream" 문자열이 정상 포함될 수 있음
  if (raw.includes("Stream failed")) return "생성 중 오류가 발생했습니다.";
  return raw;
}

export async function parseSSEStream(
  response: Response,
  onEvent: (event: ScriptStreamEvent) => void
): Promise<void> {
  if (!response.body) throw new Error("Response body is null — streaming not supported");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        if (part.startsWith("data: ")) {
          let parsed;
          try {
            parsed = JSON.parse(part.slice(6));
          } catch {
            console.warn("[SSE] malformed event skipped:", part.slice(0, 80));
            continue;
          }
          onEvent(parsed);
        }
      }
    }
  } finally {
    reader.cancel();
  }
}

export type StreamResult = { finalScenes: SceneItem[] | null; isWaiting: boolean };

export type SSEStreamOptions = {
  trackThreadId?: boolean;
  /** Called for every SSE event — used by chat UI to convert events to messages. */
  onNodeEvent?: (event: ScriptStreamEvent) => void;
};

/** Common SSE stream processing for generate & resume. */
export async function processSSEStream(
  response: Response,
  setState: React.Dispatch<React.SetStateAction<ScriptEditorState>>,
  options?: SSEStreamOptions
): Promise<StreamResult> {
  let finalScenes: SceneItem[] | null = null;
  let isWaiting = false;

  await parseSSEStream(response, (event: ScriptStreamEvent) => {
    options?.onNodeEvent?.(event);

    // Single setState per event to avoid race conditions between renders
    setState((prev) => {
      let nextSteps = updatePipelineSteps(prev.pipelineSteps, event);

      // Director plan 수신 시: skip_stages 파생 + 스텝 필터링
      if (event.node === "director_plan" && event.node_result) {
        const result = event.node_result as Record<string, unknown>;
        const directorSkip = Array.isArray(result.skip_stages)
          ? (result.skip_stages as string[])
          : [];
        nextSteps = applyDirectorPlan(nextSteps, directorSkip);
        return {
          ...prev,
          progress: { node: event.node, label: event.label, percent: event.percent },
          pipelineSteps: nextSteps,
          directorSkipStages: directorSkip,
          nodeResults: event.node_result
            ? { ...prev.nodeResults, [event.node]: event.node_result as Record<string, unknown> }
            : prev.nodeResults,
          threadId: options?.trackThreadId && event.thread_id ? event.thread_id : prev.threadId,
          traceId: event.trace_id ?? prev.traceId,
        };
      }
      let nextNodeResults = event.node_result
        ? { ...prev.nodeResults, [event.node]: event.node_result as Record<string, unknown> }
        : prev.nodeResults;

      // concept_gate의 사용자 선택을 critic 섹션에 머지
      if (event.node === "concept_gate" && event.node_result?.critic_result) {
        nextNodeResults = {
          ...nextNodeResults,
          critic: { ...nextNodeResults.critic, critic_result: event.node_result.critic_result },
        };
      }

      const base = {
        ...prev,
        progress: { node: event.node, label: event.label, percent: event.percent },
        pipelineSteps: nextSteps,
        nodeResults: nextNodeResults,
        threadId: options?.trackThreadId && event.thread_id ? event.thread_id : prev.threadId,
        traceId: event.trace_id ?? prev.traceId,
      };

      // Concept gate interrupt
      if (
        event.status === "waiting_for_input" &&
        event.node === "concept_gate" &&
        event.result?.candidates
      ) {
        const candidates = event.result.candidates;
        const selected = event.result.selected_concept;
        const recIdx = selected
          ? candidates.findIndex((c) => c.agent_role === selected.agent_role)
          : 0;
        return {
          ...base,
          concepts: candidates,
          recommendedConceptId: recIdx >= 0 ? recIdx : 0,
          isGenerating: false,
          isWaitingForConcept: true,
        };
      }

      // Director plan gate interrupt
      if (
        event.status === "waiting_for_input" &&
        event.node === "director_plan_gate" &&
        event.result?.director_plan
      ) {
        return {
          ...base,
          isGenerating: false,
          isWaitingForPlan: true,
        };
      }

      // Human gate interrupt (review approval)
      if (event.status === "waiting_for_input") {
        const draftScenes = event.result?.scenes ? mapEventScenes(event.result.scenes) : [];
        const nr = event.result?.review_result
          ? { ...base.nodeResults, review: event.result.review_result as Record<string, unknown> }
          : base.nodeResults;
        return {
          ...base,
          scenes: draftScenes.length > 0 ? draftScenes : prev.scenes,
          isGenerating: false,
          isWaitingForInput: true,
          nodeResults: nr,
          productionSnapshot: event.result?.production_snapshot ?? null,
        };
      }

      return base;
    });

    // Phase 20-B: 캐스팅 추천 → Zustand 스토어 저장 (setState 밖에서 직접 실행)
    if (event.node === "inventory_resolve" && event.node_result) {
      const c = event.node_result as Record<string, unknown>;
      if (typeof c.character_name === "string") {
        useStoryboardStore.getState().set({
          castingRecommendation: {
            character_id: typeof c.character_id === "number" ? c.character_id : null,
            character_name: c.character_name as string,
            character_b_id: typeof c.character_b_id === "number" ? c.character_b_id : null,
            character_b_name: typeof c.character_b_name === "string" ? c.character_b_name : "",
            structure: typeof c.structure === "string" ? c.structure : null,
            style_profile_id: typeof c.style_profile_id === "number" ? c.style_profile_id : null,
            reasoning: typeof c.reasoning === "string" ? c.reasoning : "",
          },
        });
      }
    }

    if (event.status === "completed" && event.result?.scenes) {
      finalScenes = mapEventScenes(event.result.scenes);
      // Sound Designer → RenderStore auto-populate
      if (event.result.sound_recommendation) {
        useRenderStore.getState().set({
          bgmPrompt: event.result.sound_recommendation.prompt || "",
          bgmMood: event.result.sound_recommendation.mood || "",
          bgmMode: "auto",
        });
      }
    }
    if (event.status === "waiting_for_input") {
      isWaiting = true;
    }
    if (event.status === "error") {
      throw new Error(friendlyErrorMessage(event.error ?? "Stream failed"));
    }
  });

  return { finalScenes, isWaiting };
}
