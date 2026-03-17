import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API_BASE, ADMIN_API_BASE } from "../constants";
import { useUIStore } from "../store/useUIStore";

// ── Types ──────────────────────────────────────────────

export type TrashItem = {
  id: number;
  name: string | null;
  deleted_at: string;
  type: "storyboard" | "character" | "group";
};

export type FilterType = "all" | "storyboard" | "character" | "group";

// ── Hook ───────────────────────────────────────────────

export function useTrashTab(
  confirmDialog: (opts: {
    title?: string;
    message?: string;
    confirmLabel?: string;
    variant?: "default" | "danger";
  }) => Promise<boolean | string>
) {
  const [items, setItems] = useState<TrashItem[]>([]);
  const [filter, setFilter] = useState<FilterType>("all");
  const [loading, setLoading] = useState(true);
  const showToast = useUIStore((s) => s.showToast);

  const fetchTrash = useCallback(async () => {
    setLoading(true);
    try {
      const [sbRes, charRes, groupRes] = await Promise.all([
        axios.get<{ id: number; title: string; deleted_at: string }[]>(
          `${API_BASE}/storyboards/trash`
        ),
        axios.get<{ id: number; name: string; deleted_at: string }[]>(
          `${API_BASE}/characters/trash`
        ),
        axios.get<{ id: number; name: string; deleted_at: string }[]>(`${API_BASE}/groups/trash`),
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
        ...groupRes.data.map((g) => ({
          id: g.id,
          name: g.name,
          deleted_at: g.deleted_at,
          type: "group" as const,
        })),
      ];

      all.sort((a, b) => new Date(b.deleted_at).getTime() - new Date(a.deleted_at).getTime());
      setItems(all);
    } catch {
      showToast("휴지통 로드에 실패했습니다", "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    void fetchTrash();
  }, [fetchTrash]);

  const handleRestore = useCallback(
    async (item: TrashItem) => {
      const endpointMap: Record<TrashItem["type"], string> = {
        storyboard: `/storyboards/${item.id}/restore`,
        character: `/characters/${item.id}/restore`,
        group: `/groups/${item.id}/restore`,
      };
      try {
        await axios.post(`${API_BASE}${endpointMap[item.type]}`);
        showToast("복원 완료", "success");
        void fetchTrash();
      } catch {
        showToast("복원에 실패했습니다", "error");
      }
    },
    [showToast, fetchTrash]
  );

  const handlePermanentDelete = useCallback(
    async (item: TrashItem) => {
      const ok = await confirmDialog({
        title: "Permanent Delete",
        message: `Permanently delete "${item.name || "Untitled"}"? This cannot be undone.`,
        confirmLabel: "삭제",
        variant: "danger",
      });
      if (!ok) return;

      const endpointMap: Record<TrashItem["type"], string> = {
        storyboard: `/storyboards/${item.id}/permanent`,
        character: `/characters/${item.id}/permanent`,
        group: `/groups/${item.id}/permanent`,
      };
      // permanent delete uses Admin API
      const base = ADMIN_API_BASE;
      try {
        await axios.delete(`${base}${endpointMap[item.type]}`);
        showToast("영구 삭제 완료", "success");
        void fetchTrash();
      } catch {
        showToast("삭제에 실패했습니다", "error");
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
