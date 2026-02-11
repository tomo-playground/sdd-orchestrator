"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useStoryboards } from "../../hooks/useStoryboards";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import StoryboardCard from "../../(app)/storyboards/StoryboardCard";
import Button from "../ui/Button";

type Props = {
  selectedId: number | null;
};

export default function ScriptListPanel({ selectedId }: Props) {
  const router = useRouter();
  const { projectId, groupId, projects, groups } = useProjectGroups();

  const [filterProjectId, setFilterProjectId] = useState<number | null>(null);
  const [filterGroupId, setFilterGroupId] = useState<number | null>(null);
  const [search, setSearch] = useState("");

  const effectiveProjectId = filterProjectId ?? projectId;
  const effectiveGroupId = filterGroupId ?? groupId;

  const filteredGroups = useMemo(
    () => groups.filter((g) => g.project_id === effectiveProjectId),
    [groups, effectiveProjectId]
  );

  const { storyboards, isLoading } = useStoryboards(effectiveProjectId, effectiveGroupId);

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

        {/* Filters */}
        <div className="flex gap-2">
          <select
            value={effectiveProjectId ?? ""}
            onChange={(e) => {
              setFilterProjectId(e.target.value ? Number(e.target.value) : null);
              setFilterGroupId(null);
            }}
            className="flex-1 rounded-lg border border-zinc-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-zinc-400"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <select
            value={effectiveGroupId ?? ""}
            onChange={(e) => setFilterGroupId(e.target.value ? Number(e.target.value) : null)}
            className="flex-1 rounded-lg border border-zinc-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-zinc-400"
          >
            <option value="">All Groups</option>
            {filteredGroups.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
        </div>

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search scripts..."
          className="mt-2 w-full rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs outline-none focus:border-zinc-400"
        />
      </div>

      {/* List */}
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {isLoading ? (
          <p className="py-8 text-center text-xs text-zinc-400">Loading...</p>
        ) : filtered.length === 0 ? (
          <p className="py-8 text-center text-xs text-zinc-400">No scripts found</p>
        ) : (
          filtered.map((sb) => (
            <div
              key={sb.id}
              className={`rounded-xl transition ${selectedId === sb.id ? "ring-2 ring-zinc-900 ring-offset-1" : ""}`}
            >
              <StoryboardCard sb={sb} onClick={() => router.push(`/scripts?id=${sb.id}`)} />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
