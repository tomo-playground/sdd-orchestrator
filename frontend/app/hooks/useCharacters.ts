"use client";

import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import type { Character, CharacterFull } from "../types";
import { API_BASE } from "../constants";

type UseCharactersResult = {
  characters: Character[];
  isLoading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  getCharacterFull: (id: number) => Promise<CharacterFull | null>;
  buildCharacterPrompt: (character: CharacterFull) => string;
  buildCharacterNegative: (character: CharacterFull) => string;
};

/**
 * Hook to load and manage characters.
 * Provides methods to fetch character details and build prompts.
 */
export function useCharacters(): UseCharactersResult {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCharacters = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      console.log("[useCharacters] Fetching from:", `${API_BASE}/characters`);
      const res = await axios.get(`${API_BASE}/characters`);
      console.log("[useCharacters] Response:", res.data?.length ?? 0, "characters");
      setCharacters(res.data || []);
    } catch (err) {
      console.error("[useCharacters] Error:", err);
      setError("Failed to load characters");
      setCharacters([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCharacters();
  }, [loadCharacters]);

  const getCharacterFull = useCallback(async (id: number): Promise<CharacterFull | null> => {
    try {
      const res = await axios.get(`${API_BASE}/characters/${id}/full`);
      return res.data;
    } catch {
      return null;
    }
  }, []);

  // Gender-related tags to filter out (will be added dynamically from character.gender)
  const GENDER_TAGS = ["1girl", "1boy", "1other", "female", "male", "woman", "man", "girl", "boy"];

  /**
   * Build a prompt string from character tags and LoRAs.
   * Format: gender tag + identity tags (filtered) + clothing tags + LoRA triggers + LoRA syntax
   */
  const buildCharacterPrompt = useCallback((character: CharacterFull): string => {
    const parts: string[] = [];

    // 1. Add gender tag from character.gender (dynamic)
    if (character.gender) {
      const genderTag = character.gender === "female" ? "1girl" : "1boy";
      parts.push(genderTag);
    }

    // 2. Add identity tags (filter out gender tags to avoid duplication)
    if (character.identity_tags.length > 0) {
      const identityTags = character.identity_tags
        .map((t) => t.name)
        .filter((name) => !GENDER_TAGS.includes(name.toLowerCase()));
      parts.push(...identityTags);
    }

    // 3. Add clothing tags
    if (character.clothing_tags.length > 0) {
      const clothingTags = character.clothing_tags.map((t) => t.name);
      parts.push(...clothingTags);
    }

    // 4. Add LoRA trigger words and syntax (supports multiple LoRAs)
    if (character.loras && character.loras.length > 0) {
      for (const lora of character.loras) {
        if (lora.trigger_words && lora.trigger_words.length > 0) {
          parts.push(...lora.trigger_words);
        }
        parts.push(`<lora:${lora.name}:${lora.weight}>`);
      }
    }

    return parts.join(", ");
  }, []);

  /**
   * Build a negative prompt string from character's recommended_negative.
   */
  const buildCharacterNegative = useCallback((character: CharacterFull): string => {
    if (character.recommended_negative && character.recommended_negative.length > 0) {
      return character.recommended_negative.join(", ");
    }
    return "";
  }, []);

  return {
    characters,
    isLoading,
    error,
    reload: loadCharacters,
    getCharacterFull,
    buildCharacterPrompt,
    buildCharacterNegative,
  };
}
