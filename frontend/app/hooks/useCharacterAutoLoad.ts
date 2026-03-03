"use client";

import { useEffect, useRef } from "react";
import axios from "axios";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useUIStore } from "../store/useUIStore";
import { useCharacters } from "./useCharacters";
import { API_BASE } from "../constants";

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

  // Load IP-Adapter reference images on mount
  useEffect(() => {
    axios
      .get(`${API_BASE}/controlnet/ip-adapter/references`)
      .then((res) => {
        const refs = res.data.references || [];
        referenceImagesRef.current = refs;
        useStoryboardStore.getState().set({ referenceImages: refs });
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
      const match = refs.length > 0 ? refs.find((r) => r.character_id === charFull.id) : null;
      sbSet({
        selectedCharacterName: charFull.name,
        basePromptA: basePrompt,
        baseNegativePromptA: baseNegative,
        loraTriggerWords: triggers,
        characterLoras,
        useIpAdapter: !!match,
        ipAdapterReference: match?.character_key || "",
        ipAdapterWeight: match?.preset?.weight ?? charFull.ip_adapter_weight ?? 0.75,
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
      const matchB = refs.length > 0 ? refs.find((r) => r.character_id === charFull.id) : null;

      sbSet({
        selectedCharacterBName: charFull.name,
        basePromptB: basePrompt,
        baseNegativePromptB: baseNegative,
        characterBLoras: loras,
        ipAdapterReferenceB: matchB?.character_key || "",
        ipAdapterWeightB: matchB?.preset?.weight ?? charFull.ip_adapter_weight ?? 0.75,
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
