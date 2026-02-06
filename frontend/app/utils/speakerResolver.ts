import type { Scene } from "../types";

export type SpeakerResolverState = {
  selectedCharacterId: number | null;
  selectedCharacterBId: number | null;
};

/**
 * Resolve speaker label to the correct character_id.
 *
 * - "A" → selectedCharacterId (Character A)
 * - "B" → selectedCharacterBId (Character B, Dialogue mode)
 * - "Narrator" → null (background-only scene, no character)
 */
export function resolveCharacterIdForSpeaker(
  speaker: Scene["speaker"],
  state: SpeakerResolverState
): number | null {
  if (speaker === "Narrator") {
    return null; // Narrator scenes show environment only (no_humans)
  }
  if (speaker === "B") {
    return state.selectedCharacterBId;
  }
  return state.selectedCharacterId;
}

export type IpAdapterResolverState = {
  ipAdapterReference: string;
  ipAdapterWeight: number;
  ipAdapterReferenceB: string;
  ipAdapterWeightB: number;
};

/**
 * Resolve IP-Adapter reference for a speaker.
 *
 * - "A" → ipAdapterReference (Character A)
 * - "B" → ipAdapterReferenceB (Character B, Dialogue mode)
 * - "Narrator" → empty (background-only scene, no character reference)
 */
export function resolveIpAdapterForSpeaker(
  speaker: Scene["speaker"],
  state: IpAdapterResolverState
): { reference: string; weight: number } {
  if (speaker === "Narrator") {
    return { reference: "", weight: 0 }; // Narrator scenes: no IP-Adapter
  }
  if (speaker === "B") {
    return { reference: state.ipAdapterReferenceB, weight: state.ipAdapterWeightB };
  }
  return { reference: state.ipAdapterReference, weight: state.ipAdapterWeight };
}

/**
 * Resolve negative prompt for a speaker.
 *
 * - "A" → baseNegativePromptA
 * - "B" → baseNegativePromptB
 * - "Narrator" → baseNegativePromptA (background scenes still need negative prompts)
 */
export function resolveNegativePromptForSpeaker(
  speaker: Scene["speaker"],
  baseNegativePromptA: string,
  baseNegativePromptB: string
): string {
  if (speaker === "B") {
    return baseNegativePromptB;
  }
  return baseNegativePromptA;
}

/**
 * Resolve base prompt for a speaker.
 *
 * - "A" → basePromptA
 * - "B" → basePromptB
 * - "Narrator" → basePromptA (for style consistency, but character tags excluded via LoRA)
 */
export function resolveBasePromptForSpeaker(
  speaker: Scene["speaker"],
  basePromptA: string,
  basePromptB: string
): string {
  if (speaker === "B") {
    return basePromptB;
  }
  return basePromptA;
}

export type CharacterLora = {
  id: number;
  name: string;
  weight?: number;
  trigger_words?: string[];
  lora_type?: string;
  optimal_weight?: number;
};

/**
 * Resolve character LoRAs for a speaker.
 *
 * Style LoRA Unification: All speakers use character LoRAs only.
 * Style LoRAs come from StyleProfile (applied uniformly to all scenes).
 *
 * - "A" → characterLoras filtered to identity only
 * - "B" → characterBLoras filtered to identity only
 * - "Narrator" → empty array (no character, style from StyleProfile)
 *
 * Note: This ensures visual consistency across A, B, and Narrator scenes
 * by using a single style source (StyleProfile) for all scenes.
 */
export function resolveCharacterLorasForSpeaker(
  speaker: Scene["speaker"],
  characterLoras: CharacterLora[],
  characterBLoras: CharacterLora[]
): CharacterLora[] {
  if (speaker === "Narrator") {
    // Narrator: no character LoRAs (background-only, style from StyleProfile)
    return [];
  }
  if (speaker === "B") {
    // B: character LoRAs only (style from StyleProfile)
    return characterBLoras.filter((l) => l.lora_type === "character");
  }
  // A: character LoRAs only (style from StyleProfile)
  return characterLoras.filter((l) => l.lora_type === "character");
}
