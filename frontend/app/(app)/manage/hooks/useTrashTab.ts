import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";
import { useStudioStore } from "../../../store/useStudioStore";

// ── Types ──────────────────────────────────────────────

export type TrashItem = {
  id: number;
  name: string | null;
  deleted_at: string;
  type: "storyboard" | "character" | "prompt_history";
};

export type FilterType = "all" | "storyboard" | "character" | "prompt_history";

// ── Hook ───────────────────────────────────────────────

export function useTrashTab(
  confirmDialog: (opts: {
    title?: string;
    message?: string;
    confirmLabel?: string;
    variant?: "default" | "danger";
  }) => Promise<boolean>
) {
  const [items, setItems] = useState<TrashItem[]>([]);
  const [filter, setFilter] = useState<FilterType>("all");
  const [loading, setLoading] = useState(true);
  const showToast = useStudioStore((s) => s.showToast);

  const fetchTrash = useCallback(async () => {
    setLoading(true);
    try {
      const [sbRes, charRes, phRes] = await Promise.all([
        axios.get<{ id: number; title: string; deleted_at: string }[]>(
          `${API_BASE}/storyboards/trash`
        ),
        axios.get<{ id: number; name: string; deleted_at: string }[]>(
          `${API_BASE}/characters/trash`
        ),
        axios.get<{ id: number; name: string; deleted_at: string }[]>(
          `${API_BASE}/prompt-histories/trash`
        ),
      ]);

      const all: TrashItem[] = [
        ...sbRes.data.map((s) => ({
          id: s.id,
          name: s.title,
          deleted_at: s.deleted_at,
          type: "storyboard" as const,
        })),
        ...charRes.data.map((c) => ({
          id: c.id,
          name: c.name,
          deleted_at: c.deleted_at,
          type: "character" as const,
        })),
        ...phRes.data.map((p) => ({
          id: p.id,
          name: p.name,
          deleted_at: p.deleted_at,
          type: "prompt_history" as const,
        })),
      ];

      all.sort((a, b) => new Date(b.deleted_at).getTime() - new Date(a.deleted_at).getTime());
      setItems(all);
    } catch {
      showToast("Failed to load trash", "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    void fetchTrash();
  }, [fetchTrash]);

  const handleRestore = useCallback(
    async (item: TrashItem) => {
      const endpoint =
        item.type === "storyboard"
          ? `/storyboards/${item.id}/restore`
          : item.type === "character"
            ? `/characters/${item.id}/restore`
            : `/prompt-histories/${item.id}/restore`;
      try {
        await axios.post(`${API_BASE}${endpoint}`);
        showToast("Restored", "success");
        void fetchTrash();
      } catch {
        showToast("Restore failed", "error");
      }
    },
    [showToast, fetchTrash]
  );

  const handlePermanentDelete = useCallback(
    async (item: TrashItem) => {
      const ok = await confirmDialog({
        title: "Permanent Delete",
        message: `Permanently delete "${item.name || "Untitled"}"? This cannot be undone.`,
        confirmLabel: "Delete",
        variant: "danger",
      });
      if (!ok) return;

      const endpoint =
        item.type === "storyboard"
          ? `/storyboards/${item.id}/permanent`
          : item.type === "character"
            ? `/characters/${item.id}/permanent`
            : `/prompt-histories/${item.id}/permanent`;
      try {
        await axios.delete(`${API_BASE}${endpoint}`);
        showToast("Permanently deleted", "success");
        void fetchTrash();
      } catch {
        showToast("Delete failed", "error");
      }
    },
    [showToast, fetchTrash, confirmDialog]
  );

  const filtered = filter === "all" ? items : items.filter((i) => i.type === filter);

  return {
    items,
    filter,
    setFilter,
    loading,
    filtered,
    handleRestore,
    handlePermanentDelete,
  };
}
