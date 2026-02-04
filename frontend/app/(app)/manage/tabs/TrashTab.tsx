"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";

type TrashItem = {
  id: number;
  name: string | null;
  title?: string;
  deleted_at: string;
  type: "storyboard" | "character" | "prompt_history";
};

type FilterType = "all" | "storyboard" | "character" | "prompt_history";

const RETENTION_DAYS = 30;

function daysRemaining(deletedAt: string): number {
  const deleted = new Date(deletedAt);
  const now = new Date();
  const diff = RETENTION_DAYS - Math.floor((now.getTime() - deleted.getTime()) / 86_400_000);
  return Math.max(0, diff);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

const TYPE_BADGE: Record<TrashItem["type"], { label: string; color: string }> = {
  storyboard: { label: "Storyboard", color: "bg-blue-100 text-blue-700" },
  character: { label: "Character", color: "bg-purple-100 text-purple-700" },
  prompt_history: { label: "Prompt", color: "bg-amber-100 text-amber-700" },
};

export default function TrashTab() {
  const [items, setItems] = useState<TrashItem[]>([]);
  const [filter, setFilter] = useState<FilterType>("all");
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const showToast = useCallback((message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

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

  const handleRestore = async (item: TrashItem) => {
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
  };

  const handlePermanentDelete = async (item: TrashItem) => {
    if (!confirm(`Permanently delete "${item.name || "Untitled"}"? This cannot be undone.`)) return;

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
  };

  const filtered = filter === "all" ? items : items.filter((i) => i.type === filter);

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-base font-bold tracking-tight">Trash</h2>

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2">
        {(["all", "storyboard", "character", "prompt_history"] as FilterType[]).map((f) => {
          const labels: Record<FilterType, string> = {
            all: "All",
            storyboard: "Storyboards",
            character: "Characters",
            prompt_history: "Prompts",
          };
          const count = f === "all" ? items.length : items.filter((i) => i.type === f).length;
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                filter === f
                  ? "bg-zinc-900 text-white"
                  : "border border-zinc-200 bg-white text-zinc-500 hover:bg-zinc-50"
              }`}
            >
              {labels[f]} ({count})
            </button>
          );
        })}
      </div>

      {/* List */}
      {loading ? (
        <p className="py-8 text-center text-sm text-zinc-400">Loading...</p>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-zinc-400">
          <span className="text-3xl">&#128465;</span>
          <p className="text-sm">Trash is empty</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {filtered.map((item) => {
            const badge = TYPE_BADGE[item.type];
            const remaining = daysRemaining(item.deleted_at);
            return (
              <div
                key={`${item.type}-${item.id}`}
                className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-4 py-3"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${badge.color}`}
                  >
                    {badge.label}
                  </span>
                  <span className="truncate text-sm font-medium text-zinc-800">
                    {item.name || "Untitled"}
                  </span>
                  <span className="shrink-0 text-[11px] text-zinc-400">
                    {formatDate(item.deleted_at)}
                  </span>
                  <span className="shrink-0 text-[11px] text-zinc-400">{remaining}d left</span>
                </div>

                <div className="ml-3 flex shrink-0 gap-2">
                  <button
                    onClick={() => handleRestore(item)}
                    className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 transition hover:bg-zinc-50"
                  >
                    Restore
                  </button>
                  <button
                    onClick={() => handlePermanentDelete(item)}
                    className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-100"
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          className={`fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl px-5 py-3 text-sm font-medium shadow-lg transition ${
            toast.type === "success" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"
          }`}
        >
          {toast.message}
        </div>
      )}
    </section>
  );
}
