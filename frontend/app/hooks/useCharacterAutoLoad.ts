"use client";

import { useEffect, useRef } from "react";
import axios from "axios";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useUIStore } from "../store/useUIStore";
import { useCharacters } from "./useCharacters";
import { API_BASE } from "../constants";
import type { ReferenceImage } from "../types";

/**
 * Auto-load character LoRA/prompt settings and IP-Adapter references.
 * Extracted from PlanTab's useEffects.
 */
export function useCharacterAutoLoad() {
  const selectedCharacterId = useStoryboardStore((s) => s.selectedCharacterId);
  const selectedCharacterBId = useStoryboardStore((s) => s.selectedCharacterBId);
  const sbSet = useStoryboardStore((s) => s.set);
  const referenceImagesRef = useRef(useStoryboardStore.getState().referenceImages);
  const prevCharIdRef = useRef<number | null>(null);
  const prevCharBIdRef = useRef<number | null>(null);

  const { getCharacterFull, buildCharacterPrompt, buildCharacterNegative } = useCharacters();
  // refs 로드 완료 여부 — character effect가 refs 미로드 시 useIpAdapter를 건드리지 않도록 분리
  const refsLoadedRef = useRef(false);

  // Load IP-Adapter reference images on mount
  useEffect(() => {
    axios
      .get(`${API_BASE}/controlnet/ip-adapter/references`)
      .then((res) => {
        const refs: ReferenceImage[] = res.data.references || [];
        referenceImagesRef.current = refs;
        refsLoadedRef.current = true;
        useStoryboardStore.getState().set({ referenceImages: refs });

        // Race condition fix: character effect가 refs 로드 전에 실행된 경우 재평가
        // (mount 시점에만 발생, 사용자 조작 이후에는 refs가 이미 로드됨)
        const state = useStoryboardStore.getState();
        const updates: Partial<typeof state> = {};

        if (state.selectedCharacterId) {
          const matchA = refs.find((r) => r.character_id === state.selectedCharacterId);
          if (matchA && !state.ipAdapterReference) {
            updates.useIpAdapter = true;
            updates.ipAdapterReference = matchA.character_key;
            updates.ipAdapterWeight = matchA.preset?.weight ?? state.ipAdapterWeight ?? 0.75;
          }
        }

        if (state.selectedCharacterBId) {
          const matchB = refs.find((r) => r.character_id === state.selectedCharacterBId);
          if (matchB && !state.ipAdapterReferenceB) {
            updates.ipAdapterReferenceB = matchB.character_key;
            updates.ipAdapterWeightB = matchB.preset?.weight ?? state.ipAdapterWeightB ?? 0.75;
          }
        }

        if (Object.keys(updates).length > 0) {
          useStoryboardStore.getState().set(updates);
        }
      })
      .catch((err) =>
        console.warn("[useCharacterAutoLoad] IP-Adapter references fetch failed:", err)
      );
  }, []);

  // Auto-load character A LoRA/prompt settings when character changes
  useEffect(() => {
    if (!selectedCharacterId) {
      sbSet({
        loraTriggerWords: [],
        characterLoras: [],
        selectedCharacterName: null,
        basePromptA: "",
        baseNegativePromptA: "",
      });
      return;
    }
    getCharacterFull(selectedCharacterId).then((charFull) => {
      if (!charFull) return;

      const basePrompt = buildCharacterPrompt(charFull);
      const baseNegative = buildCharacterNegative(charFull);
      const triggers = charFull.loras?.length
        ? charFull.loras.flatMap((l) => l.trigger_words || [])
        : [];
      const characterLoras = charFull.loras?.length
        ? charFull.loras.map((l) => ({
            id: l.id,
            name: l.name,
            weight: l.weight,
            trigger_words: l.trigger_words,
            lora_type: l.lora_type,
            optimal_weight: l.optimal_weight,
          }))
        : [];

      const refs = referenceImagesRef.current;
      const match = refs.find((r) => r.character_id === charFull.id) ?? null;
      // refs 로드 완료 시에만 IP-Adapter 상태 확정 — 미로드 시 재평가는 refs effect에서 처리
      const ipAdapterUpdates = refsLoadedRef.current
        ? {
            useIpAdapter: !!match,
            ipAdapterReference: match?.character_key || "",
            ipAdapterWeight: match?.preset?.weight ?? charFull.ip_adapter_weight ?? 0.75,
          }
        : {};
      sbSet({
        selectedCharacterName: charFull.name,
        basePromptA: basePrompt,
        baseNegativePromptA: baseNegative,
        loraTriggerWords: triggers,
        characterLoras,
        ...ipAdapterUpdates,
      });

      // 초기 로드가 아닌 캐릭터 전환 시에만 stale 경고
      const wasChange =
        prevCharIdRef.current !== null && prevCharIdRef.current !== selectedCharacterId;
      prevCharIdRef.current = selectedCharacterId;
      if (wasChange) {
        const sceneCount = useStoryboardStore.getState().scenes.length;
        if (sceneCount > 0) {
          useUIStore.getState().showToast("캐릭터 변경됨 — 프롬프트 갱신이 필요합니다", "warning");
        }
      }
    });
  }, [selectedCharacterId, getCharacterFull, buildCharacterPrompt, buildCharacterNegative, sbSet]);

  // Auto-load character B data when selectedCharacterBId changes
  useEffect(() => {
    if (!selectedCharacterBId) {
      sbSet({
        characterBLoras: [],
        selectedCharacterBName: null,
        basePromptB: "",
        baseNegativePromptB: "",
      });
      return;
    }
    getCharacterFull(selectedCharacterBId).then((charFull) => {
      if (!charFull) return;
      const basePrompt = buildCharacterPrompt(charFull);
      const baseNegative = buildCharacterNegative(charFull);
      const loras = charFull.loras?.length
        ? charFull.loras.map((l) => ({
            id: l.id,
            name: l.name,
            weight: l.weight,
            trigger_words: l.trigger_words,
            lora_type: l.lora_type,
            optimal_weight: l.optimal_weight,
          }))
        : [];

      const refs = referenceImagesRef.current;
      const matchB = refs.find((r) => r.character_id === charFull.id) ?? null;
      const ipAdapterBUpdates = refsLoadedRef.current
        ? {
            ipAdapterReferenceB: matchB?.character_key || "",
            ipAdapterWeightB: matchB?.preset?.weight ?? charFull.ip_adapter_weight ?? 0.75,
          }
        : {};
      sbSet({
        selectedCharacterBName: charFull.name,
        basePromptB: basePrompt,
        baseNegativePromptB: baseNegative,
        characterBLoras: loras,
        ...ipAdapterBUpdates,
      });

      // 초기 로드가 아닌 캐릭터 전환 시에만 stale 경고
      const wasChange =
        prevCharBIdRef.current !== null && prevCharBIdRef.current !== selectedCharacterBId;
      prevCharBIdRef.current = selectedCharacterBId;
      if (wasChange) {
        const sceneCount = useStoryboardStore.getState().scenes.length;
        if (sceneCount > 0) {
          useUIStore
            .getState()
            .showToast("캐릭터 B 변경됨 — 프롬프트 갱신이 필요합니다", "warning");
        }
      }
    });
  }, [selectedCharacterBId, getCharacterFull, buildCharacterPrompt, buildCharacterNegative, sbSet]);
}
