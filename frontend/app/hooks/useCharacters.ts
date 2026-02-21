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
      const res = await axios.get<{ items: Character[] }>(`${API_BASE}/characters`);
      setCharacters(res.data.items ?? []);
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
      const res = await axios.get(`${API_BASE}/characters/${id}`);
      return res.data;
    } catch {
      return null;
    }
  }, []);

  /**
   * Build a prompt string from character's DB tags + custom_base_prompt.
   * Includes identity/clothing tags from V3 character_tags relationship.
   */
  const buildCharacterPrompt = useCallback((character: CharacterFull): string => {
    const parts: string[] = [];

    // 1. Include V3 DB tags (identity, clothing, etc.)
    if (character.tags?.length) {
      for (const tag of character.tags) {
        if (!tag.name) continue;
        if (tag.weight !== 1.0) {
          parts.push(`(${tag.name}:${tag.weight})`);
        } else {
          parts.push(tag.name);
        }
      }
    }

    // 2. Append custom_base_prompt tokens (avoid duplicates)
    if (character.custom_base_prompt) {
      const existing = new Set(parts.map((p) => p.replace(/[():\d.]/g, "").toLowerCase()));
      const custom = character.custom_base_prompt
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      for (const token of custom) {
        const norm = token.replace(/[():\d.]/g, "").toLowerCase();
        if (!existing.has(norm)) {
          parts.push(token);
        }
      }
    }

    return parts.join(", ");
  }, []);

  /**
   * Build a negative prompt string from character's custom_negative_prompt.
   * SSOT: Character Edit Modal - use exactly what user configured, no auto-combining.
   */
  const buildCharacterNegative = useCallback((character: CharacterFull): string => {
    // Return custom_negative_prompt as-is (user's configured value)
    return character.custom_negative_prompt || "";
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
