"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { format } from "date-fns";
import { API_BASE } from "../../constants";
import LoadingSpinner from "../ui/LoadingSpinner";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import type { GroupItem } from "../../types";

interface StoryboardItem {
  id: number;
  title: string;
  description: string | null;
  scene_count: number;
  image_count: number;
  group_id: number | null;
  created_at: string | null;
  updated_at: string | null;
}

type Props = {
  projectId: number | null;
  groupId: number | null;
  groups: GroupItem[];
  selectGroup: (id: number) => void;
  showToast: (message: string, type: "success" | "error") => void;
};

export default function StoryboardsSection({
  projectId,
  groupId,
  groups,
  selectGroup,
  showToast,
}: Props) {
  const router = useRouter();
  const [storyboards, setStoryboards] = useState<StoryboardItem[]>([]);
  const [sbLoading, setSbLoading] = useState(true);
  const [showNewSbModal, setShowNewSbModal] = useState(false);
  const [newSbTitle, setNewSbTitle] = useState("");

  const openNewStoryboard = useCallback(() => {
    setNewSbTitle("");
    setShowNewSbModal(true);
  }, []);

  const confirmNewStoryboard = useCallback(() => {
    if (!groupId) return;
    selectGroup(groupId);
    const params = new URLSearchParams({ new: "true" });
    if (newSbTitle.trim()) params.set("title", newSbTitle.trim());
    router.push(`/studio?${params.toString()}`);
  }, [groupId, newSbTitle, selectGroup, router]);

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
    <>
      <section>
        {/* Header: New Storyboard CTA */}
        {groups.length > 0 && (
          <div className="mb-4 flex items-center justify-end">
            <Button
              size="sm"
              onClick={openNewStoryboard}
              className="shrink-0 rounded-full"
            >
              + New Storyboard
            </Button>
          </div>
        )}

        {sbLoading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="md" />
          </div>
        ) : storyboards.length === 0 ? (
          <EmptyState
            hasGroups={groups.length > 0}
            onNewStoryboard={openNewStoryboard}
          />
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

      {/* New Storyboard Title Modal */}
      {showNewSbModal && (
        <Modal open onClose={() => setShowNewSbModal(false)} size="sm">
          <Modal.Header>
            <h2 className="text-sm font-bold text-zinc-900">New Storyboard</h2>
            <button
              onClick={() => setShowNewSbModal(false)}
              className="text-xs text-zinc-400 hover:text-zinc-600"
            >
              x
            </button>
          </Modal.Header>
          <div className="px-5 py-4">
            <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
              Topic *
            </label>
            <input
              value={newSbTitle}
              onChange={(e) => setNewSbTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newSbTitle.trim()) confirmNewStoryboard();
              }}
              placeholder="e.g. 에어컨 소리 30초 쇼츠"
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
              autoFocus
            />
          </div>
          <Modal.Footer>
            <Button variant="ghost" size="sm" onClick={() => setShowNewSbModal(false)}>
              Cancel
            </Button>
            <Button size="sm" disabled={!newSbTitle.trim()} onClick={confirmNewStoryboard}>
              Create
            </Button>
          </Modal.Footer>
        </Modal>
      )}
    </>
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
