"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { Clapperboard } from "lucide-react";
import { useStudioStore } from "../../store/useStudioStore";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import { useStoryboards } from "../../hooks/useStoryboards";
import StoryboardCard, { DraftCard } from "./StoryboardCard";
import Button from "../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../components/ui/ConfirmDialog";
import EmptyState from "../../components/ui/EmptyState";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import { CONTAINER_CLASSES, PAGE_TITLE_CLASSES, SEARCH_INPUT_CLASSES } from "../../components/ui/variants";
import { API_BASE } from "../../constants";

export default function StoryboardsPage() {
  const router = useRouter();
  const showToast = useStudioStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();

  const { projectId, groupId } = useProjectGroups();
  const [search, setSearch] = useState("");

  const { storyboards, isLoading, remove } = useStoryboards(projectId, groupId);

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
      <div className="mb-6 flex items-center justify-between">
        <h1 className={PAGE_TITLE_CLASSES}>
          Storyboards{!isLoading && storyboards.length > 0 ? ` (${storyboards.length})` : ""}
        </h1>
        <Button size="sm" onClick={() => router.push("/studio?new=true")}>
          + New Storyboard
        </Button>
      </div>

      <div className="mb-6">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search storyboards..."
          className={SEARCH_INPUT_CLASSES}
        />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="md" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Clapperboard}
          title={storyboards.length === 0 ? "No storyboards yet" : "No storyboards match your search"}
          description={
            storyboards.length === 0
              ? "Create a storyboard to start producing shorts"
              : "Try a different search term"
          }
          action={
            storyboards.length === 0 ? (
              <Button size="md" onClick={() => router.push("/studio?new=true")}>
                + New Storyboard
              </Button>
            ) : undefined
          }
        />
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
