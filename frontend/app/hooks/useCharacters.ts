"use client";

import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import type { Character, CharacterFull } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
      const res = await axios.get(`${API_BASE}/characters`);
      setCharacters(res.data || []);
    } catch {
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

  /**
   * Build a prompt string from character tags and LoRAs.
   * Format: identity tags + clothing tags + LoRA triggers + LoRA syntax
   */
  const buildCharacterPrompt = useCallback((character: CharacterFull): string => {
    const parts: string[] = [];

    // Add identity tags (subject, hair_color, eye_color, etc.)
    if (character.identity_tags.length > 0) {
      const identityTags = character.identity_tags.map((t) => t.name);
      parts.push(...identityTags);
    }

    // Add clothing tags
    if (character.clothing_tags.length > 0) {
      const clothingTags = character.clothing_tags.map((t) => t.name);
      parts.push(...clothingTags);
    }

    // Add LoRA trigger words and syntax (supports multiple LoRAs)
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
