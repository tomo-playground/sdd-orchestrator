/**
 * Hook for tag validation and auto-replacement
 */

import { useState, useCallback } from "react";
import axios from "axios";
import type { TagValidationResult } from "../components/prompt/TagValidationWarning";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type UseTagValidationResult = {
  validationResult: TagValidationResult | null;
  isValidating: boolean;
  validateTags: (tags: string[], checkDanbooru?: boolean) => Promise<TagValidationResult | null>;
  autoReplaceTags: (tags: string[]) => Promise<string[] | null>;
  clearValidation: () => void;
};

export default function useTagValidation(): UseTagValidationResult {
  const [validationResult, setValidationResult] = useState<TagValidationResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  const validateTags = useCallback(async (
    tags: string[],
    checkDanbooru: boolean = true
  ): Promise<TagValidationResult | null> => {
    if (tags.length === 0) {
      setValidationResult(null);
      return null;
    }

    setIsValidating(true);
    try {
      const response = await axios.post(`${API_BASE}/prompt/validate-tags`, {
        tags,
        check_danbooru: checkDanbooru,
      });
      setValidationResult(response.data);
      return response.data;
    } catch (error) {
      console.error("Tag validation error:", error);
      return null;
    } finally {
      setIsValidating(false);
    }
  }, []);

  const autoReplaceTags = useCallback(async (tags: string[]): Promise<string[] | null> => {
    try {
      const response = await axios.post(`${API_BASE}/prompt/auto-replace`, {
        tags,
      });
      return response.data.replaced;
    } catch (error) {
      console.error("Auto-replace error:", error);
      return null;
    }
  }, []);

  const clearValidation = useCallback(() => {
    setValidationResult(null);
  }, []);

  return {
    validationResult,
    isValidating,
    validateTags,
    autoReplaceTags,
    clearValidation,
  };
}
