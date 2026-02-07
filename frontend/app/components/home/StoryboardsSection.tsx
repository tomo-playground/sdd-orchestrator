"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { format } from "date-fns";
import { API_BASE } from "../../constants";
import { useStudioStore } from "../../store/useStudioStore";
import LoadingSpinner from "../ui/LoadingSpinner";
import Button from "../ui/Button";
import { LABEL_CLASSES } from "../ui/variants";
import type { GroupItem } from "../../types";

interface CastMember {
  id: number;
  name: string;
  speaker: string;
  preview_url: string | null;
}

interface StoryboardItem {
  id: number;
  title: string;
  description: string | null;
  scene_count: number;
  image_count: number;
  group_id: number | null;
  cast: CastMember[];
  created_at: string | null;
  updated_at: string | null;
}

type Props = {
  projectId: number | null;
  groupId: number | null;
  groups: GroupItem[];
};

export default function StoryboardsSection({ projectId, groupId, groups }: Props) {
  const router = useRouter();
  const showToast = useStudioStore((s) => s.showToast);
  const [storyboards, setStoryboards] = useState<StoryboardItem[]>([]);
  const [sbLoading, setSbLoading] = useState(true);

  const navigateToNewStoryboard = useCallback(() => {
    if (!groupId) return;
    router.push("/studio?new=true");
  }, [groupId, router]);

  // Fetch storyboards filtered by sidebar's selected group
  useEffect(() => {
    if (projectId === null) return;
    setSbLoading(true); // eslint-disable-line react-hooks/set-state-in-effect
    const params: Record<string, unknown> = { project_id: projectId };
    if (groupId) params.group_id = groupId;
    axios
      .get(`${API_BASE}/storyboards`, { params })
      .then((res) => setStoryboards(res.data))
      .catch(() => showToast("Failed to load storyboards", "error"))
      .finally(() => setSbLoading(false));
  }, [projectId, groupId, showToast]);

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this storyboard?")) return;
    try {
      await axios.delete(`${API_BASE}/storyboards/${id}`);
      setStoryboards((prev) => prev.filter((s) => s.id !== id));
      showToast("Storyboard deleted", "success");
    } catch {
      showToast("Failed to delete", "error");
    }
  };

  return (
    <section>
      {/* Header */}
      {groups.length > 0 && (
        <div className="mb-4 flex items-center justify-between">
          <h2 className={LABEL_CLASSES}>
            Storyboards{!sbLoading && storyboards.length > 0 ? ` (${storyboards.length})` : ""}
          </h2>
          {!sbLoading && storyboards.length > 0 && (
            <Button size="sm" onClick={navigateToNewStoryboard} className="shrink-0 rounded-full">
              + New Storyboard
            </Button>
          )}
        </div>
      )}

      {sbLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="md" />
        </div>
      ) : storyboards.length === 0 ? (
        <EmptyState hasGroups={groups.length > 0} onNewStoryboard={navigateToNewStoryboard} />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <DraftCard onClick={() => router.push("/studio")} />
          {storyboards.map((sb) => (
            <StoryboardCard
              key={sb.id}
              sb={sb}
              onClick={() => router.push(`/studio?id=${sb.id}`)}
              onDelete={() => handleDelete(sb.id)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

/* ---- Sub-components ---- */

function EmptyState({
  hasGroups,
  onNewStoryboard,
}: {
  hasGroups: boolean;
  onNewStoryboard: () => void;
}) {
  return (
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
        <p className="text-sm font-medium text-zinc-500">No storyboards in this group</p>
        <p className="mt-1 text-xs text-zinc-400">
          {hasGroups
            ? "Create a storyboard to start producing shorts"
            : "Select a group from the sidebar to get started"}
        </p>
      </div>
      {hasGroups && (
        <Button size="md" onClick={onNewStoryboard}>
          + New Storyboard
        </Button>
      )}
    </div>
  );
}

function StoryboardCard({
  sb,
  onClick,
  onDelete,
}: {
  sb: StoryboardItem;
  onClick: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      data-testid={`storyboard-card-${sb.id}`}
      className="group relative flex cursor-pointer flex-col gap-2 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm transition hover:shadow-md"
      onClick={onClick}
    >
      <h3 className="line-clamp-1 text-sm font-semibold text-zinc-900">{sb.title}</h3>
      {sb.description && <p className="line-clamp-2 text-xs text-zinc-500">{sb.description}</p>}
      <div className="flex items-center gap-3 text-[10px] text-zinc-400">
        <span>{sb.scene_count} scenes</span>
        <span>{sb.image_count} images</span>
        {sb.updated_at && <span>{format(new Date(sb.updated_at), "yyyy.MM.dd")}</span>}
      </div>
      {/* Cast thumbnails */}
      {sb.cast && sb.cast.length > 0 && (
        <div className="mt-1 flex items-center gap-1">
          {sb.cast.map((c) => (
            <div
              key={c.id}
              title={`${c.speaker}: ${c.name}`}
              className="h-6 w-6 shrink-0 overflow-hidden rounded-full border border-zinc-200 bg-zinc-100"
            >
              {c.preview_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={c.preview_url}
                  alt={c.name}
                  className="h-full w-full object-cover object-top"
                />
              ) : (
                <span className="flex h-full w-full items-center justify-center text-[8px] text-zinc-400">
                  {c.speaker}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="absolute top-3 right-3 text-xs text-zinc-300 opacity-0 transition group-hover:opacity-100 hover:text-red-400"
        title="Delete"
      >
        x
      </button>
    </div>
  );
}

function DraftCard({ onClick }: { onClick: () => void }) {
  const [hasDraft, setHasDraft] = useState(false);

  useEffect(() => {
    try {
      const stored =
        localStorage.getItem("shorts-producer:studio:v1") ||
        localStorage.getItem("shorts-producer:draft:v1");
      if (stored) {
        const data = JSON.parse(stored);
        const state = data?.state || data;
        if (state?.topic || (state?.scenes && state.scenes.length > 0)) {
          setHasDraft(true); // eslint-disable-line react-hooks/set-state-in-effect
        }
      }
    } catch {}
  }, []);

  if (!hasDraft) return null;

  return (
    <div
      onClick={onClick}
      className="flex cursor-pointer flex-col gap-2 rounded-2xl border-2 border-dashed border-zinc-300 bg-zinc-50 p-4 transition hover:border-zinc-400"
    >
      <span className="text-xs font-semibold text-zinc-600">Continue Draft</span>
      <span className="text-[10px] text-zinc-400">Resume your unsaved work</span>
    </div>
  );
}
