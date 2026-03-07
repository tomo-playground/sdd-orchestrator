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
      const items = res.data.items ?? [];
      setCharacters(items);

      // ConnectionGuard용 캐릭터 프리뷰 캐시 (Backend 다운 시 사용)
      try {
        const previews = items
          .filter((c) => c.reference_image_url)
          .map((c) => ({ name: c.name, url: c.reference_image_url! }));
        if (previews.length > 0) {
          localStorage.setItem("character_previews", JSON.stringify(previews));
        }
      } catch {
        // localStorage 접근 실패 무시
      }
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
   * Build a prompt string from character's DB tags + positive_prompt.
   * Includes identity/clothing tags from character_tags relationship.
   */
  const buildCharacterPrompt = useCallback((character: CharacterFull): string => {
    const parts: string[] = [];

    // 1. Include DB tags (identity, clothing, etc.)
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

    // 2. Append positive_prompt tokens (avoid duplicates)
    if (character.positive_prompt) {
      const existing = new Set(parts.map((p) => p.replace(/[():\d.]/g, "").toLowerCase()));
      const custom = character.positive_prompt
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
   * Build a negative prompt string from character's negative_prompt.
   * SSOT: Character Edit Modal - use exactly what user configured, no auto-combining.
   */
  const buildCharacterNegative = useCallback((character: CharacterFull): string => {
    return character.negative_prompt || "";
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
