"use client";

import { useState, useCallback, useRef } from "react";
import { ADMIN_API_BASE } from "../constants";

type ClassificationResult = {
  group: string | null;
  confidence: number;
  source: string;
};

type ClassifyResponse = {
  results: Record<string, ClassificationResult>;
  classified: number;
  unknown: number;
};

// Module-level cache (persists across component re-renders)
const classificationCache = new Map<string, string | null>();

/**
 * Hook for dynamic tag classification using backend API.
 * Replaces hardcoded getTokenCategory() patterns.
 */
export function useTagClassifier() {
  const [isLoading, setIsLoading] = useState(false);
  const pendingRef = useRef<Set<string>>(new Set());

  /**
   * Get category for a single tag (from cache or returns null if not cached)
   */
  const getCachedCategory = useCallback((tag: string): string | null => {
    const normalized = tag.toLowerCase().trim();
    return classificationCache.get(normalized) ?? null;
  }, []);

  /**
   * Classify multiple tags via API (batch operation)
   */
  const classifyTags = useCallback(
    async (tags: string[]): Promise<Record<string, string | null>> => {
      if (tags.length === 0) return {};

      // Filter out already cached tags
      const uncached = tags.filter((t) => {
        const normalized = t.toLowerCase().trim();
        return !classificationCache.has(normalized) && !pendingRef.current.has(normalized);
      });

      // If all cached, return from cache
      if (uncached.length === 0) {
        return tags.reduce(
          (acc, tag) => {
            acc[tag] = classificationCache.get(tag.toLowerCase().trim()) ?? null;
            return acc;
          },
          {} as Record<string, string | null>
        );
      }

      // Mark as pending
      uncached.forEach((t) => pendingRef.current.add(t.toLowerCase().trim()));
      setIsLoading(true);

      try {
        const response = await fetch(`${ADMIN_API_BASE}/tags/classify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tags: uncached }),
        });

        if (!response.ok) {
          throw new Error(`Classification failed: ${response.status}`);
        }

        const data: ClassifyResponse = await response.json();

        // Update cache with results
        Object.entries(data.results).forEach(([tag, result]) => {
          const normalized = tag.toLowerCase().trim();
          classificationCache.set(normalized, result.group);
          pendingRef.current.delete(normalized);
        });

        // Return all results (cached + new)
        return tags.reduce(
          (acc, tag) => {
            acc[tag] = classificationCache.get(tag.toLowerCase().trim()) ?? null;
            return acc;
          },
          {} as Record<string, string | null>
        );
      } catch (error) {
        console.error("[TagClassifier] Error:", error);
        // Clear pending on error
        uncached.forEach((t) => pendingRef.current.delete(t.toLowerCase().trim()));
        return {};
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Pre-warm cache with common tags
   */
  const preloadTags = useCallback(
    async (tags: string[]) => {
      await classifyTags(tags);
    },
    [classifyTags]
  );

  /**
   * Clear the classification cache
   */
  const clearCache = useCallback(() => {
    classificationCache.clear();
  }, []);

  return {
    classifyTags,
    getCachedCategory,
    preloadTags,
    clearCache,
    isLoading,
    cacheSize: classificationCache.size,
  };
}

// Export cache for debugging
export const getClassificationCache = () => classificationCache;
