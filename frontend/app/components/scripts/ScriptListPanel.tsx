"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { API_BASE, SCRIPTS_LIST_REFRESH } from "../../constants";
import { useStoryboards } from "../../hooks/useStoryboards";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import { useUIStore } from "../../store/useUIStore";
import StoryboardCard from "../../(app)/storyboards/StoryboardCard";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";
import Button from "../ui/Button";
import LoadingSpinner from "../ui/LoadingSpinner";

type Props = {
  selectedId: number | null;
};

export default function ScriptListPanel({ selectedId }: Props) {
  const router = useRouter();
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();
  const { projectId, groupId } = useProjectGroups();

  const [search, setSearch] = useState("");

  const { storyboards, isLoading, reload, remove } = useStoryboards(projectId, groupId);

  // Listen for list-refresh events from editors
  useEffect(() => {
    const handler = () => reload();
    window.addEventListener(SCRIPTS_LIST_REFRESH, handler);
    return () => window.removeEventListener(SCRIPTS_LIST_REFRESH, handler);
  }, [reload]);

  const handleDelete = useCallback(
    async (id: number) => {
      const ok = await confirm({
        title: "Delete Script",
        message: "Delete this script?",
        variant: "danger",
      });
      if (!ok) return;
      try {
        await axios.delete(`${API_BASE}/storyboards/${id}`);
        remove(id);
        if (selectedId === id) router.push("/scripts");
        showToast("Script deleted", "success");
      } catch {
        showToast("Failed to delete", "error");
      }
    },
    [confirm, remove, selectedId, router, showToast]
  );

  const filtered = useMemo(() => {
    if (!search.trim()) return storyboards;
    const q = search.toLowerCase();
    return storyboards.filter(
      (sb) => sb.title.toLowerCase().includes(q) || sb.description?.toLowerCase().includes(q)
    );
  }, [storyboards, search]);

  return (
    <div className="flex h-full flex-col border-r border-zinc-200 bg-zinc-50/50">
      {/* Header */}
      <div className="border-b border-zinc-200 px-4 py-3">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-bold text-zinc-900">Scripts</h2>
          <Button size="sm" onClick={() => router.push("/scripts?new=true")}>
            + New
          </Button>
        </div>

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search scripts..."
          className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs outline-none focus:border-zinc-400"
        />
      </div>

      {/* List */}
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {isLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="sm" />
          </div>
        ) : filtered.length === 0 ? (
          <p className="py-8 text-center text-xs text-zinc-400">No scripts found</p>
        ) : (
          filtered.map((sb) => (
            <div
              key={sb.id}
              className={`rounded-xl transition ${selectedId === sb.id ? "ring-2 ring-zinc-900 ring-offset-1" : ""}`}
            >
              <StoryboardCard
                sb={sb}
                onClick={() => router.push(`/scripts?id=${sb.id}`)}
                onDelete={() => handleDelete(sb.id)}
              />
            </div>
          ))
        )}
      </div>
      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
