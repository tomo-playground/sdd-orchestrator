"use client";

import { useEffect } from "react";
import axios from "axios";
import { useStudioStore } from "../store/useStudioStore";
import { useCharacters } from "./useCharacters";
import { API_BASE } from "../constants";

/**
 * Auto-load character LoRA/prompt settings and IP-Adapter references.
 * Extracted from PlanTab's useEffects.
 */
export function useCharacterAutoLoad() {
  const selectedCharacterId = useStudioStore((s) => s.selectedCharacterId);
  const selectedCharacterBId = useStudioStore((s) => s.selectedCharacterBId);
  const referenceImages = useStudioStore((s) => s.referenceImages);
  const setPlan = useStudioStore((s) => s.setPlan);

  const { getCharacterFull, buildCharacterPrompt, buildCharacterNegative } = useCharacters();

  // Load IP-Adapter reference images on mount
  useEffect(() => {
    axios
      .get(`${API_BASE}/controlnet/ip-adapter/references`)
      .then((res) => {
        useStudioStore.getState().setScenesState({
          referenceImages: res.data.references || [],
        });
      })
      .catch(() => {});
  }, []);

  // Auto-load character A LoRA/prompt settings when character changes
  useEffect(() => {
    if (!selectedCharacterId) {
      setPlan({
        loraTriggerWords: [],
        characterLoras: [],
        characterPromptMode: "auto",
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

      const mode =
        charFull.prompt_mode || (charFull.effective_mode === "lora" ? "lora" : "standard");

      const match =
        referenceImages.length > 0
          ? referenceImages.find((r) => r.character_id === charFull.id)
          : null;
      setPlan({
        selectedCharacterName: charFull.name,
        basePromptA: basePrompt,
        baseNegativePromptA: baseNegative,
        loraTriggerWords: triggers,
        characterLoras,
        characterPromptMode: mode || "auto",
        useIpAdapter: !!match,
        ipAdapterReference: match?.character_key || "",
        ipAdapterWeight: match?.preset?.weight ?? charFull.ip_adapter_weight ?? 0.75,
      });
    });
  }, [
    selectedCharacterId,
    referenceImages,
    getCharacterFull,
    buildCharacterPrompt,
    buildCharacterNegative,
    setPlan,
  ]);

  // Auto-load character B data when selectedCharacterBId changes
  useEffect(() => {
    if (!selectedCharacterBId) {
      setPlan({
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

      const matchB =
        referenceImages.length > 0
          ? referenceImages.find((r) => r.character_id === charFull.id)
          : null;

      setPlan({
        selectedCharacterBName: charFull.name,
        basePromptB: basePrompt,
        baseNegativePromptB: baseNegative,
        characterBLoras: loras,
        ipAdapterReferenceB: matchB?.character_key || "",
        ipAdapterWeightB: matchB?.preset?.weight ?? charFull.ip_adapter_weight ?? 0.75,
      });
    });
  }, [
    selectedCharacterBId,
    referenceImages,
    getCharacterFull,
    buildCharacterPrompt,
    buildCharacterNegative,
    setPlan,
  ]);
}
