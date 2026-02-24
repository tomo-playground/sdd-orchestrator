import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import type { Tag } from "../types";

const DEBOUNCE_MS = 300;
const KOREAN_RE = /[가-힣\u3130-\u318F]/;
const VALID_WORD_RE = /^[a-zA-Z0-9_\-()가-힣\u3130-\u318F]+$/;

type UseTagSuggestionOptions = {
  inputRef: React.RefObject<HTMLElement | null>;
  dropdownRef: React.RefObject<HTMLDivElement | null>;
};

export default function useTagSuggestion({ inputRef, dropdownRef }: UseTagSuggestionOptions) {
  const [suggestions, setSuggestions] = useState<Tag[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [dropdownRef, inputRef]);

  const fetchSuggestions = useCallback(async (query: string) => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    try {
      const res = await axios.get(`${API_BASE}/tags/search`, {
        params: { q: query, limit: 10 },
        signal: controller.signal,
      });
      setSuggestions(res.data);
      setHighlightedIndex(0);
      setIsOpen(true);
    } catch (err) {
      if (!axios.isCancel(err)) console.error("Tag search failed", err);
    }
  }, []);

  /** Check min length (Korean 1 / Latin 2) and debounce the API call. */
  const triggerSearch = useCallback(
    (word: string) => {
      const hasKorean = KOREAN_RE.test(word);
      const minLen = hasKorean ? 1 : 2;

      if (word.length >= minLen && VALID_WORD_RE.test(word)) {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
          void fetchSuggestions(word);
        }, DEBOUNCE_MS);
      } else {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        setIsOpen(false);
      }
    },
    [fetchSuggestions]
  );

  const closeSuggestions = useCallback(() => {
    setIsOpen(false);
    setSuggestions([]);
  }, []);

  /**
   * Handle ArrowUp/Down/Escape navigation keys.
   * Returns true if the key was handled (caller should preventDefault).
   */
  const handleNavigationKey = useCallback(
    (key: string): boolean => {
      if (!isOpen || suggestions.length === 0) return false;

      if (key === "ArrowDown") {
        setHighlightedIndex((prev) => (prev + 1) % suggestions.length);
        return true;
      }
      if (key === "ArrowUp") {
        setHighlightedIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
        return true;
      }
      if (key === "Escape") {
        setIsOpen(false);
        return true;
      }
      return false;
    },
    [isOpen, suggestions.length]
  );

  return {
    suggestions,
    isOpen,
    highlightedIndex,
    setHighlightedIndex,
    triggerSearch,
    closeSuggestions,
    handleNavigationKey,
    dropdownRef,
  };
}
