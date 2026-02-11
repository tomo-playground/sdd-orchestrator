"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import { useStoryboards } from "../../hooks/useStoryboards";
import StoryboardCard, { DraftCard } from "./StoryboardCard";
import Button from "../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../components/ui/ConfirmDialog";
import { CONTAINER_CLASSES } from "../../components/ui/variants";
import { API_BASE } from "../../constants";

export default function StoryboardsPage() {
  const router = useRouter();
  const showToast = useStudioStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();

  // Read global project/group for initial values only
  const { projectId, groupId, projects, groups } = useProjectGroups();

  // Local filter state — does NOT reset Studio state
  const [filterProjectId, setFilterProjectId] = useState<number | null>(null);
  const [filterGroupId, setFilterGroupId] = useState<number | null>(null);
  const [search, setSearch] = useState("");

  // Use global values as defaults until user explicitly changes filter
  const effectiveProjectId = filterProjectId ?? projectId;
  const effectiveGroupId = filterGroupId ?? groupId;

  // Filter groups by selected project
  const filteredGroups = useMemo(
    () => groups.filter((g) => g.project_id === effectiveProjectId),
    [groups, effectiveProjectId]
  );

  const { storyboards, isLoading, remove } = useStoryboards(effectiveProjectId, effectiveGroupId);

  // Client-side search filter
  const filtered = useMemo(() => {
    if (!search.trim()) return storyboards;
    const q = search.toLowerCase();
    return storyboards.filter(
      (sb) => sb.title.toLowerCase().includes(q) || sb.description?.toLowerCase().includes(q)
    );
  }, [storyboards, search]);

  const handleDelete = async (id: number) => {
    const ok = await confirm({
      title: "Delete Storyboard",
      message: "Delete this storyboard? This cannot be undone.",
      confirmLabel: "Delete",
      variant: "danger",
    });
    if (!ok) return;
    try {
      await axios.delete(`${API_BASE}/storyboards/${id}`);
      remove(id);
      showToast("Storyboard deleted", "success");
    } catch {
      showToast("Failed to delete", "error");
    }
  };

  return (
    <div className={`${CONTAINER_CLASSES} py-8`}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-lg font-bold text-zinc-900">
          Storyboards{!isLoading && storyboards.length > 0 ? ` (${storyboards.length})` : ""}
        </h1>
        <Button size="sm" onClick={() => router.push("/studio?new=true")}>
          + New Storyboard
        </Button>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <select
          value={effectiveProjectId ?? ""}
          onChange={(e) => {
            const id = e.target.value ? Number(e.target.value) : null;
            setFilterProjectId(id);
            setFilterGroupId(null);
          }}
          className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <select
          value={effectiveGroupId ?? ""}
          onChange={(e) => {
            setFilterGroupId(e.target.value ? Number(e.target.value) : null);
          }}
          className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
        >
          <option value="">All Groups</option>
          {filteredGroups.map((g) => (
            <option key={g.id} value={g.id}>
              {g.name}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search storyboards..."
          className="flex-1 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
        />
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="py-16 text-center text-sm text-zinc-400">Loading storyboards...</div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <svg
            className="h-12 w-12 text-zinc-200"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-1.5A1.125 1.125 0 0118 18.375M20.625 4.5H3.375m17.25 0c.621 0 1.125.504 1.125 1.125M20.625 4.5h-1.5C18.504 4.5 18 5.004 18 5.625m3.75 0v1.5c0 .621-.504 1.125-1.125 1.125M3.375 4.5c-.621 0-1.125.504-1.125 1.125M3.375 4.5h1.5C5.496 4.5 6 5.004 6 5.625m-3.75 0v1.5c0 .621.504 1.125 1.125 1.125m0 0h1.5m-1.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m1.5-3.75C5.496 8.25 6 7.746 6 7.125v-1.5M4.875 8.25C5.496 8.25 6 8.754 6 9.375v1.5m0-5.25v5.25m0-5.25C6 5.004 6.504 4.5 7.125 4.5h9.75c.621 0 1.125.504 1.125 1.125"
            />
          </svg>
          <div>
            <p className="text-sm font-medium text-zinc-500">
              {storyboards.length === 0 ? "No storyboards yet" : "No storyboards match your search"}
            </p>
            <p className="mt-1 text-xs text-zinc-400">
              {storyboards.length === 0
                ? "Create a storyboard to start producing shorts"
                : "Try a different search term"}
            </p>
          </div>
          {storyboards.length === 0 && (
            <Button size="md" onClick={() => router.push("/studio?new=true")}>
              + New Storyboard
            </Button>
          )}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <DraftCard onClick={() => router.push("/studio")} />
          {filtered.map((sb) => (
            <StoryboardCard
              key={sb.id}
              sb={sb}
              onClick={() => router.push(`/studio?id=${sb.id}`)}
              onDelete={() => handleDelete(sb.id)}
            />
          ))}
        </div>
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
