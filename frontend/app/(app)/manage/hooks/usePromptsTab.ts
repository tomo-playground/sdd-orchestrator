import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { API_BASE, PROMPT_APPLY_KEY } from "../../../constants";
import type { PromptHistory } from "../../../types";

// ── Hook ───────────────────────────────────────────────

export function usePromptsTab() {
  const router = useRouter();

  const [promptHistories, setPromptHistories] = useState<PromptHistory[]>([]);
  const [isPromptsLoading, setIsPromptsLoading] = useState(false);
  const [promptsFilter, setPromptsFilter] = useState<"all" | "favorites">("all");
  const [promptsCharacterFilter, setPromptsCharacterFilter] = useState<number | null>(null);
  const [promptsSort, setPromptsSort] = useState<"created_at" | "use_count" | "avg_match_rate">(
    "created_at"
  );
  const [promptsSearch, setPromptsSearch] = useState("");
  const [deletingPromptId, setDeletingPromptId] = useState<number | null>(null);

  // Refs to avoid unnecessary deps in callbacks
  const promptsSearchRef = useRef(promptsSearch);
  promptsSearchRef.current = promptsSearch;
  const promptHistoriesRef = useRef(promptHistories);
  promptHistoriesRef.current = promptHistories;

  const fetchPromptHistories = useCallback(async () => {
    setIsPromptsLoading(true);
    try {
      const params: Record<string, unknown> = {
        sort_by: promptsSort,
        favorites_only: promptsFilter === "favorites",
        query: promptsSearchRef.current,
      };
      if (promptsCharacterFilter) {
        params.character_id = promptsCharacterFilter;
      }
      const res = await axios.get<PromptHistory[]>(`${API_BASE}/prompt-histories`, { params });
      setPromptHistories(res.data || []);
    } catch {
      setPromptHistories([]);
    } finally {
      setIsPromptsLoading(false);
    }
  }, [promptsSort, promptsFilter, promptsCharacterFilter]);

  useEffect(() => {
    void fetchPromptHistories();
  }, [fetchPromptHistories]);

  const deletePromptHistory = useCallback(async (id: number) => {
    if (!confirm("Delete this prompt history?")) return;
    setDeletingPromptId(id);
    try {
      await axios.delete(`${API_BASE}/prompt-histories/${id}`);
      setPromptHistories((prev) => prev.filter((p) => p.id !== id));
    } catch {
      alert("Failed to delete prompt");
    } finally {
      setDeletingPromptId(null);
    }
  }, []);

  const togglePromptFavorite = useCallback(async (id: number) => {
    try {
      const prompt = promptHistoriesRef.current.find((p) => p.id === id);
      if (!prompt) return;
      await axios.put(`${API_BASE}/prompt-histories/${id}`, {
        is_favorite: !prompt.is_favorite,
      });
      setPromptHistories((prev) =>
        prev.map((p) => (p.id === id ? { ...p, is_favorite: !p.is_favorite } : p)),
      );
    } catch {
      alert("Failed to update favorite status");
    }
  }, []);

  const applyPromptHistory = useCallback(
    (id: number) => {
      const prompt = promptHistoriesRef.current.find((p) => p.id === id);
      if (!prompt) return;

      // Save to localStorage so Storyboard page can pick it up
      localStorage.setItem(PROMPT_APPLY_KEY, JSON.stringify(prompt));
      router.push("/");
    },
    [router],
  );

  return {
    promptHistories,
    isPromptsLoading,
    promptsFilter,
    setPromptsFilter,
    promptsCharacterFilter,
    setPromptsCharacterFilter,
    promptsSort,
    setPromptsSort,
    promptsSearch,
    setPromptsSearch,
    deletingPromptId,
    fetchPromptHistories,
    deletePromptHistory,
    togglePromptFavorite,
    applyPromptHistory,
  };
}
