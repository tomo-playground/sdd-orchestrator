"use client";

/**
 * Shared hook for fetching tag/LoRA data and tag search.
 * Used by both CharacterWizard (new) and CharacterDetailPage (edit).
 */

import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../../../../constants";
import { useUIStore } from "../../../../store/useUIStore";
import type { Tag, LoRA } from "../../../../types";
import { WIZARD_CATEGORIES } from "../builder/wizardTemplates";

export function useTagData() {
  const showToast = useUIStore((s) => s.showToast);

  const [tagsByGroup, setTagsByGroup] = useState<Record<string, Tag[]>>({});
  const [allTagsFlat, setAllTagsFlat] = useState<Tag[]>([]);
  const [allLoras, setAllLoras] = useState<LoRA[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Search
  const [searchQuery, setSearchQueryRaw] = useState("");
  const [searchResults, setSearchResults] = useState<Tag[]>([]);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Data fetching ──────────────────────────────────────────
  useEffect(() => {
    const groups = WIZARD_CATEGORIES.map((c) => c.groupName);
    const tagFetches = groups.map((g) =>
      axios.get<Tag[]>(`${API_BASE}/tags`, { params: { group_name: g } })
    );
    const loraFetch = axios.get<LoRA[]>(`${API_BASE}/loras`);

    Promise.all([Promise.all(tagFetches), loraFetch])
      .then(([tagResponses, loraRes]) => {
        const grouped: Record<string, Tag[]> = {};
        const flat: Tag[] = [];
        tagResponses.forEach((res, i) => {
          grouped[groups[i]] = res.data;
          flat.push(...res.data);
        });
        setTagsByGroup(grouped);
        setAllTagsFlat(flat);
        setAllLoras(loraRes.data);
      })
      .catch(() => showToast("태그 데이터 로드에 실패했습니다", "error"))
      .finally(() => setIsLoading(false));
  }, [showToast]);

  // ── Search with debounce ───────────────────────────────────
  const setSearchQuery = useCallback((q: string) => {
    setSearchQueryRaw(q);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    if (!q.trim()) {
      setSearchResults([]);
      return;
    }
    searchTimerRef.current = setTimeout(async () => {
      try {
        const res = await axios.get<Tag[]>(`${API_BASE}/tags/search`, {
          params: { q },
        });
        setSearchResults(res.data.slice(0, 20));
      } catch {
        setSearchResults([]);
      }
    }, 300);
  }, []);

  return {
    tagsByGroup,
    allTagsFlat,
    allLoras,
    isLoading,
    searchQuery,
    setSearchQuery,
    searchResults,
  };
}
