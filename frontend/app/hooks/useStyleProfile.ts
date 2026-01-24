"use client";

import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import type { StyleProfileFull } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type UseStyleProfileResult = {
  styleProfile: StyleProfileFull | null;
  isLoading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  buildPrompts: () => { positive: string; negative: string } | null;
};

/**
 * Hook to load and manage the default Style Profile.
 * Provides auto-built prompts with LoRA triggers and embeddings.
 */
export function useStyleProfile(): UseStyleProfileResult {
  const [styleProfile, setStyleProfile] = useState<StyleProfileFull | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDefaultProfile = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_BASE}/style-profiles/default`);
      setStyleProfile(res.data);
    } catch (err) {
      // No default profile set - this is OK
      setStyleProfile(null);
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        setError(null); // 404 is expected if no default profile
      } else {
        setError("Failed to load style profile");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDefaultProfile();
  }, [loadDefaultProfile]);

  /**
   * Build positive and negative prompts from the Style Profile.
   * - Positive: default_positive + LoRA triggers + LoRA syntax
   * - Negative: default_negative + embedding triggers
   */
  const buildPrompts = useCallback((): { positive: string; negative: string } | null => {
    if (!styleProfile) return null;

    const positiveParts: string[] = [];
    const negativeParts: string[] = [];

    // 1. Add default positive prompt
    if (styleProfile.default_positive) {
      positiveParts.push(styleProfile.default_positive);
    }

    // 2. Add LoRA trigger words and syntax
    if (styleProfile.loras && styleProfile.loras.length > 0) {
      for (const lora of styleProfile.loras) {
        // Add trigger words
        if (lora.trigger_words && lora.trigger_words.length > 0) {
          positiveParts.push(lora.trigger_words.join(", "));
        }
        // Add LoRA syntax at the end
        positiveParts.push(`<lora:${lora.name}:${lora.weight}>`);
      }
    }

    // 3. Add default negative prompt
    if (styleProfile.default_negative) {
      negativeParts.push(styleProfile.default_negative);
    }

    // 4. Add negative embedding triggers
    if (styleProfile.negative_embeddings && styleProfile.negative_embeddings.length > 0) {
      for (const emb of styleProfile.negative_embeddings) {
        if (emb.trigger_word) {
          negativeParts.push(emb.trigger_word);
        }
      }
    }

    return {
      positive: positiveParts.join(", "),
      negative: negativeParts.join(", "),
    };
  }, [styleProfile]);

  return {
    styleProfile,
    isLoading,
    error,
    reload: loadDefaultProfile,
    buildPrompts,
  };
}
