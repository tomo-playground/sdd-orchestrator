import type { Scene } from "../types";

export type SpeakerResolverState = {
  selectedCharacterId: number | null;
  selectedCharacterBId: number | null;
};

/**
 * Resolve speaker label to the correct character_id.
 *
 * - "A" / "Narrator" → selectedCharacterId (Character A)
 * - "B" → selectedCharacterBId (Character B, Dialogue mode)
 */
export function resolveCharacterIdForSpeaker(
  speaker: Scene["speaker"],
  state: SpeakerResolverState
): number | null {
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
 * - "A" / "Narrator" → ipAdapterReference (Character A)
 * - "B" → ipAdapterReferenceB (Character B, Dialogue mode)
 */
export function resolveIpAdapterForSpeaker(
  speaker: Scene["speaker"],
  state: IpAdapterResolverState
): { reference: string; weight: number } {
  if (speaker === "B") {
    return { reference: state.ipAdapterReferenceB, weight: state.ipAdapterWeightB };
  }
  return { reference: state.ipAdapterReference, weight: state.ipAdapterWeight };
}

/**
 * Resolve negative prompt for a speaker.
 *
 * - "A" / "Narrator" → baseNegativePromptA
 * - "B" → baseNegativePromptB
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
 * - "A" / "Narrator" → basePromptA
 * - "B" → basePromptB
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
  lora_id: number;
  weight: number;
  name?: string;
  trigger_words?: string[];
  optimal_weight?: number;
};

/**
 * Resolve character LoRAs for a speaker.
 *
 * - "A" / "Narrator" → characterLoras
 * - "B" → characterBLoras
 */
export function resolveCharacterLorasForSpeaker(
  speaker: Scene["speaker"],
  characterLoras: CharacterLora[],
  characterBLoras: CharacterLora[]
): CharacterLora[] {
  if (speaker === "B") {
    return characterBLoras;
  }
  return characterLoras;
}
