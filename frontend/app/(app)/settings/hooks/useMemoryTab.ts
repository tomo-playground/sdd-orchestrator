"use client";

import { useState, useCallback, useEffect } from "react";
import { API_BASE } from "../../../constants";

// ── Types ──────────────────────────────────────────────

type MemoryStats = { total: number; by_namespace: Record<string, number> };

export type MemoryItemData = {
  namespace: string[];
  key: string;
  value: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

// ── Hook ───────────────────────────────────────────────

export function useMemoryTab() {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [items, setItems] = useState<MemoryItemData[]>([]);
  const [activeNs, setActiveNs] = useState<string>("character");
  const [loading, setLoading] = useState(false);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/memory/stats`);
      if (res.ok) setStats(await res.json());
    } catch {
      /* silent */
    }
  }, []);

  const fetchItems = useCallback(async (ns: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/memory/${ns}`);
      if (res.ok) {
        const data = await res.json();
        setItems(data.items ?? []);
      }
    } catch {
      /* silent */
    }
    setLoading(false);
  }, []);

  const deleteItem = useCallback(
    async (nsType: string, nsId: string, key: string) => {
      try {
        await fetch(`${API_BASE}/memory/${nsType}/${nsId}/${key}`, { method: "DELETE" });
        setItems((prev) => prev.filter((i) => i.key !== key));
        await fetchStats();
      } catch {
        /* silent */
      }
    },
    [fetchStats]
  );

  const deleteNamespace = useCallback(
    async (nsType: string, nsId: string) => {
      try {
        await fetch(`${API_BASE}/memory/${nsType}/${nsId}`, { method: "DELETE" });
        setItems([]);
        await fetchStats();
      } catch {
        /* silent */
      }
    },
    [fetchStats]
  );

  // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data fetch (same pattern as useTrashTab)
  useEffect(() => { void fetchStats(); }, [fetchStats]);

  // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch on namespace change
  useEffect(() => { void fetchItems(activeNs); }, [activeNs, fetchItems]);

  return {
    stats,
    items,
    activeNs,
    setActiveNs,
    loading,
    fetchStats,
    fetchItems,
    deleteItem,
    deleteNamespace,
  };
}
