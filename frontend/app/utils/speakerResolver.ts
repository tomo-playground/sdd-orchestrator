import type { Scene } from "../types";

export type SpeakerResolverState = {
  selectedCharacterId: number | null;
  selectedCharacterBId: number | null;
};

/**
 * Resolve speaker label to the correct character_id.
 *
 * - "speaker_1" → selectedCharacterId (Character A)
 * - "speaker_2" → selectedCharacterBId (Character B, Dialogue mode)
 * - "narrator" → null (background-only scene, no character)
 */
export function resolveCharacterIdForSpeaker(
  speaker: Scene["speaker"],
  state: SpeakerResolverState
): number | null {
  if (speaker === "narrator") {
    return null; // Narrator scenes show environment only (no_humans)
  }
  if (speaker === "speaker_2") {
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
 * - "speaker_1" → ipAdapterReference (Character A)
 * - "speaker_2" → ipAdapterReferenceB (Character B, Dialogue mode)
 * - "narrator" → empty (background-only scene, no character reference)
 */
export function resolveIpAdapterForSpeaker(
  speaker: Scene["speaker"],
  state: IpAdapterResolverState
): { reference: string; weight: number } {
  if (speaker === "narrator") {
    return { reference: "", weight: 0 }; // Narrator scenes: no IP-Adapter
  }
  if (speaker === "speaker_2") {
    return { reference: state.ipAdapterReferenceB, weight: state.ipAdapterWeightB };
  }
  return { reference: state.ipAdapterReference, weight: state.ipAdapterWeight };
}

/**
 * Resolve negative prompt for a speaker.
 *
 * - "speaker_1" → baseNegativePromptA
 * - "speaker_2" → baseNegativePromptB
 * - "narrator" → baseNegativePromptA (background scenes still need negative prompts)
 */
export function resolveNegativePromptForSpeaker(
  speaker: Scene["speaker"],
  baseNegativePromptA: string,
  baseNegativePromptB: string
): string {
  if (speaker === "speaker_2") {
    return baseNegativePromptB;
  }
  return baseNegativePromptA;
}

/**
 * Resolve base prompt for a speaker.
 *
 * - "speaker_1" → basePromptA
 * - "speaker_2" → basePromptB
 * - "narrator" → basePromptA (for style consistency, but character tags excluded via LoRA)
 */
export function resolveBasePromptForSpeaker(
  speaker: Scene["speaker"],
  basePromptA: string,
  basePromptB: string
): string {
  if (speaker === "speaker_2") {
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
};

/**
 * Resolve character LoRAs for a speaker.
 *
 * Style LoRA Unification: All speakers use character LoRAs only.
 * Style LoRAs come from StyleProfile (applied uniformly to all scenes).
 *
 * - "speaker_1" → characterLoras filtered to identity only
 * - "speaker_2" → characterBLoras filtered to identity only
 * - "narrator" → empty array (no character, style from StyleProfile)
 */
export function resolveCharacterLorasForSpeaker(
  speaker: Scene["speaker"],
  characterLoras: CharacterLora[],
  characterBLoras: CharacterLora[]
): CharacterLora[] {
  if (speaker === "narrator") {
    // Narrator: no character LoRAs. Style LoRAs come from StyleProfile (backend SSOT).
    return [];
  }
  if (speaker === "speaker_2") {
    // B: character LoRAs only (style from StyleProfile)
    return characterBLoras.filter((l) => l.lora_type === "character");
  }
  // A: character LoRAs only (style from StyleProfile)
  return characterLoras.filter((l) => l.lora_type === "character");
}
