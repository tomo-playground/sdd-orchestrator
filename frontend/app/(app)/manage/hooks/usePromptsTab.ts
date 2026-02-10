import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { API_BASE, PROMPT_APPLY_KEY } from "../../../constants";
import type { PromptHistory } from "../../../types";

// ── Types ──────────────────────────────────────────────

type UiCallbacks = {
  showToast: (message: string, type: "success" | "error" | "warning") => void;
  confirmDialog: (opts: {
    title?: string;
    message?: string;
    confirmLabel?: string;
    variant?: "default" | "danger";
  }) => Promise<boolean>;
};

// ── Hook ───────────────────────────────────────────────

export function usePromptsTab(ui: UiCallbacks) {
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

  const deletePromptHistory = useCallback(
    async (id: number) => {
      const ok = await ui.confirmDialog({
        title: "Delete Prompt",
        message: "Delete this prompt history?",
        confirmLabel: "Delete",
        variant: "danger",
      });
      if (!ok) return;
      setDeletingPromptId(id);
      try {
        await axios.delete(`${API_BASE}/prompt-histories/${id}`);
        setPromptHistories((prev) => prev.filter((p) => p.id !== id));
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Failed to delete prompt: ${msg}`, "error");
      } finally {
        setDeletingPromptId(null);
      }
    },
    [ui]
  );

  const togglePromptFavorite = useCallback(
    async (id: number) => {
      try {
        const prompt = promptHistoriesRef.current.find((p) => p.id === id);
        if (!prompt) return;
        await axios.put(`${API_BASE}/prompt-histories/${id}`, {
          is_favorite: !prompt.is_favorite,
        });
        setPromptHistories((prev) =>
          prev.map((p) => (p.id === id ? { ...p, is_favorite: !p.is_favorite } : p))
        );
      } catch (error) {
        const msg = axios.isAxiosError(error)
          ? (error.response?.data?.detail ?? error.message)
          : "Unknown error";
        ui.showToast(`Failed to update favorite status: ${msg}`, "error");
      }
    },
    [ui]
  );

  const applyPromptHistory = useCallback(
    (id: number) => {
      const prompt = promptHistoriesRef.current.find((p) => p.id === id);
      if (!prompt) return;

      // Save to localStorage so Storyboard page can pick it up
      localStorage.setItem(PROMPT_APPLY_KEY, JSON.stringify(prompt));
      router.push("/");
    },
    [router]
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
