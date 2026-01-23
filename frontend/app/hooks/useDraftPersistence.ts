"use client";

import { useEffect, useRef, useCallback } from "react";

const DEBOUNCE_MS = 300;

interface UseDraftPersistenceOptions<T> {
  storageKey: string;
  onHydrate: (data: T) => void;
  getDraftData: () => T;
  getSlimDraftData?: () => T;
  dependencies: unknown[];
}

export function useDraftPersistence<T>({
  storageKey,
  onHydrate,
  getDraftData,
  getSlimDraftData,
  dependencies,
}: UseDraftPersistenceOptions<T>) {
  const hasHydratedRef = useRef(false);
  const saveTimeoutRef = useRef<number | null>(null);
  const getDraftDataRef = useRef(getDraftData);
  const getSlimDraftDataRef = useRef(getSlimDraftData);
  getDraftDataRef.current = getDraftData;
  getSlimDraftDataRef.current = getSlimDraftData;

  // Hydration effect - runs once on mount
  useEffect(() => {
    if (hasHydratedRef.current) return;
    if (typeof window === "undefined") return;

    try {
      const stored = window.localStorage.getItem(storageKey);
      if (stored) {
        const data = JSON.parse(stored) as T;
        onHydrate(data);
      }
    } catch {
      // Ignore malformed data
    } finally {
      hasHydratedRef.current = true;
    }
  }, [storageKey, onHydrate]);

  // Save effect - runs when dependencies change
  useEffect(() => {
    if (!hasHydratedRef.current) return;
    if (typeof window === "undefined") return;

    if (saveTimeoutRef.current) {
      window.clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = window.setTimeout(() => {
      try {
        const data = getDraftDataRef.current();
        window.localStorage.setItem(storageKey, JSON.stringify(data));
      } catch (error) {
        if (error instanceof DOMException && error.name === "QuotaExceededError") {
          // Try saving slim version without images
          if (getSlimDraftDataRef.current) {
            try {
              const slimData = getSlimDraftDataRef.current();
              window.localStorage.setItem(storageKey, JSON.stringify(slimData));
            } catch {
              console.warn("Draft save failed: quota exceeded even with slim data");
            }
          } else {
            console.warn("Draft save failed: quota exceeded");
          }
        } else {
          console.error("Draft save failed:", error);
        }
      }
    }, DEBOUNCE_MS);

    return () => {
      if (saveTimeoutRef.current) {
        window.clearTimeout(saveTimeoutRef.current);
        saveTimeoutRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  const reset = useCallback(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      // Ignore errors
    }
  }, [storageKey]);

  const isHydrated = useCallback(() => hasHydratedRef.current, []);

  return { reset, isHydrated };
}

export type UseDraftPersistenceReturn = ReturnType<typeof useDraftPersistence>;
