"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { format } from "date-fns";
import { API_BASE } from "../../constants";
import LoadingSpinner from "../ui/LoadingSpinner";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import GroupFormModal from "../context/GroupFormModal";
import { createGroup, updateGroup } from "../../store/actions/groupActions";
import type { GroupItem } from "../../types";

const GROUP_COLORS = [
  { pill: "bg-sky-100 text-sky-700", active: "bg-sky-600 text-white", dot: "bg-sky-400" },
  { pill: "bg-emerald-100 text-emerald-700", active: "bg-emerald-600 text-white", dot: "bg-emerald-400" },
  { pill: "bg-amber-100 text-amber-700", active: "bg-amber-600 text-white", dot: "bg-amber-400" },
  { pill: "bg-rose-100 text-rose-700", active: "bg-rose-600 text-white", dot: "bg-rose-400" },
  { pill: "bg-violet-100 text-violet-700", active: "bg-violet-600 text-white", dot: "bg-violet-400" },
  { pill: "bg-teal-100 text-teal-700", active: "bg-teal-600 text-white", dot: "bg-teal-400" },
];

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
  groups: GroupItem[];
  selectGroup: (id: number) => void;
  showToast: (message: string, type: "success" | "error") => void;
};

export default function StoryboardsSection({ projectId, groups, selectGroup, showToast }: Props) {
  const router = useRouter();
  const [storyboards, setStoryboards] = useState<StoryboardItem[]>([]);
  const [sbLoading, setSbLoading] = useState(true);
  const [filterGroupId, setFilterGroupId] = useState<number | null>(null);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState<GroupItem | null>(null);
  const [showNewSbModal, setShowNewSbModal] = useState(false);
  const [newSbTitle, setNewSbTitle] = useState("");
  const [pendingGroupId, setPendingGroupId] = useState<number | null>(null);

  const openNewStoryboard = useCallback((gid: number) => {
    setPendingGroupId(gid);
    setNewSbTitle("");
    setShowNewSbModal(true);
  }, []);

  const confirmNewStoryboard = useCallback(() => {
    if (!pendingGroupId) return;
    selectGroup(pendingGroupId);
    const params = new URLSearchParams({ new: "true" });
    if (newSbTitle.trim()) params.set("title", newSbTitle.trim());
    router.push(`/studio?${params.toString()}`);
  }, [pendingGroupId, newSbTitle, selectGroup, router]);

  // Reset group filter when project changes
  useEffect(() => {
    setFilterGroupId(null); // eslint-disable-line react-hooks/set-state-in-effect
  }, [projectId]);

  // Fetch storyboards
  useEffect(() => {
    if (projectId === null) return;
    setSbLoading(true); // eslint-disable-line react-hooks/set-state-in-effect
    const params: Record<string, unknown> = { project_id: projectId };
    if (filterGroupId) params.group_id = filterGroupId;
    axios
      .get(`${API_BASE}/storyboards`, { params })
      .then((res) => setStoryboards(res.data))
      .catch(() => showToast("Failed to load storyboards", "error"))
      .finally(() => setSbLoading(false));
  }, [projectId, filterGroupId, showToast]);

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
        {/* Group filter + actions */}
        <div className="mb-4 flex items-center justify-between gap-3">
          {/* Left: filter pills + new group */}
          <div className="flex items-center gap-1.5 overflow-x-auto min-w-0">
            {groups.length > 0 && (
              <button
                onClick={() => setFilterGroupId(null)}
                className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition ${
                  filterGroupId === null
                    ? "bg-zinc-900 text-white"
                    : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                }`}
              >
                All
              </button>
            )}
            {groups.map((g, idx) => {
              const color = GROUP_COLORS[idx % GROUP_COLORS.length];
              return (
                <span key={g.id} className="group/pill relative shrink-0">
                  <button
                    onClick={() => { setFilterGroupId(g.id); selectGroup(g.id); }}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                      filterGroupId === g.id ? color.active : color.pill
                    }`}
                  >
                    {g.name}
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setEditingGroup(g); }}
                    className="absolute -right-1 -top-1 hidden h-4 w-4 items-center justify-center rounded-full bg-zinc-200 text-[8px] text-zinc-500 hover:bg-zinc-300 hover:text-zinc-700 group-hover/pill:flex"
                    title="Edit group"
                  >
                    <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
                    </svg>
                  </button>
                </span>
              );
            })}
            <button
              onClick={() => setShowGroupModal(true)}
              className="shrink-0 rounded-full border border-dashed border-zinc-300 px-3 py-1 text-xs text-zinc-400 hover:border-zinc-400 hover:text-zinc-600 transition"
            >
              + New Group
            </button>
          </div>
          {/* Right: primary CTA */}
          {groups.length > 0 && (
            <button
              onClick={() => openNewStoryboard(filterGroupId ?? groups[0].id)}
              className="shrink-0 rounded-full bg-zinc-900 px-3 py-1 text-xs font-semibold text-white hover:bg-zinc-800 transition"
            >
              + New Storyboard
            </button>
          )}
        </div>

        {sbLoading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="md" />
          </div>
        ) : storyboards.length === 0 ? (
          <EmptyState
            groups={groups}
            filterGroupId={filterGroupId}
            onNewGroup={() => setShowGroupModal(true)}
            onNewStoryboard={() => openNewStoryboard(filterGroupId ?? groups[0]?.id)}
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <DraftCard onClick={() => router.push("/studio")} />
            {storyboards.map((sb) => (
              <StoryboardCard
                key={sb.id}
                sb={sb}
                groups={groups}
                filterGroupId={filterGroupId}
                onClick={() => router.push(`/studio?id=${sb.id}`)}
                onDelete={() => handleDelete(sb.id)}
              />
            ))}
          </div>
        )}
      </section>

      {/* Group Create Modal */}
      {showGroupModal && projectId && (
        <GroupFormModal
          projectId={projectId}
          onSave={async (data) => {
            const g = await createGroup(data as Parameters<typeof createGroup>[0]);
            if (g) {
              selectGroup(g.id);
              if (groups.length === 0) openNewStoryboard(g.id);
            }
          }}
          onClose={() => setShowGroupModal(false)}
        />
      )}

      {/* Group Edit Modal */}
      {editingGroup && projectId && (
        <GroupFormModal
          group={editingGroup}
          projectId={projectId}
          onSave={async (data) => { await updateGroup(editingGroup.id, data); }}
          onClose={() => setEditingGroup(null)}
        />
      )}

      {/* New Storyboard Title Modal */}
      {showNewSbModal && (
        <Modal open onClose={() => setShowNewSbModal(false)} size="sm">
          <Modal.Header>
            <h2 className="text-sm font-bold text-zinc-900">New Storyboard</h2>
            <button onClick={() => setShowNewSbModal(false)} className="text-zinc-400 hover:text-zinc-600 text-xs">x</button>
          </Modal.Header>
          <div className="px-5 py-4">
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
              Topic *
            </label>
            <input
              value={newSbTitle}
              onChange={(e) => setNewSbTitle(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && newSbTitle.trim()) confirmNewStoryboard(); }}
              placeholder="e.g. 에어컨 소리 30초 쇼츠"
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
              autoFocus
            />
          </div>
          <Modal.Footer>
            <Button variant="ghost" size="sm" onClick={() => setShowNewSbModal(false)}>Cancel</Button>
            <Button size="sm" disabled={!newSbTitle.trim()} onClick={confirmNewStoryboard}>Create</Button>
          </Modal.Footer>
        </Modal>
      )}
    </>
  );
}

/* ---- Sub-components ---- */

function EmptyState({
  groups,
  filterGroupId,
  onNewGroup,
  onNewStoryboard,
}: {
  groups: GroupItem[];
  filterGroupId: number | null;
  onNewGroup: () => void;
  onNewStoryboard: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-4 py-16 text-center">
      <svg className="h-12 w-12 text-zinc-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-1.5A1.125 1.125 0 0118 18.375M20.625 4.5H3.375m17.25 0c.621 0 1.125.504 1.125 1.125M20.625 4.5h-1.5C18.504 4.5 18 5.004 18 5.625m3.75 0v1.5c0 .621-.504 1.125-1.125 1.125M3.375 4.5c-.621 0-1.125.504-1.125 1.125M3.375 4.5h1.5C5.496 4.5 6 5.004 6 5.625m-3.75 0v1.5c0 .621.504 1.125 1.125 1.125m0 0h1.5m-1.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m1.5-3.75C5.496 8.25 6 7.746 6 7.125v-1.5M4.875 8.25C5.496 8.25 6 8.754 6 9.375v1.5m0-5.25v5.25m0-5.25C6 5.004 6.504 4.5 7.125 4.5h9.75c.621 0 1.125.504 1.125 1.125" />
      </svg>
      <div>
        <p className="text-sm font-medium text-zinc-500">
          {filterGroupId ? "No storyboards in this group" : "No storyboards yet"}
        </p>
        <p className="mt-1 text-xs text-zinc-400">
          {groups.length === 0
            ? "Create a group first to start organizing storyboards"
            : "Create a storyboard to start producing shorts"}
        </p>
      </div>
      <button
        onClick={groups.length === 0 ? onNewGroup : onNewStoryboard}
        className="rounded-full bg-zinc-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-zinc-800 transition"
      >
        {groups.length === 0 ? "+ Create Group" : "+ New Storyboard"}
      </button>
    </div>
  );
}

function StoryboardCard({
  sb,
  groups,
  filterGroupId,
  onClick,
  onDelete,
}: {
  sb: StoryboardItem;
  groups: GroupItem[];
  filterGroupId: number | null;
  onClick: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      data-testid={`storyboard-card-${sb.id}`}
      className="group relative flex flex-col gap-2 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm hover:shadow-md transition cursor-pointer"
      onClick={onClick}
    >
      <h3 className="text-sm font-semibold text-zinc-900 line-clamp-1">{sb.title}</h3>
      {sb.description && (
        <p className="text-xs text-zinc-500 line-clamp-2">{sb.description}</p>
      )}
      <div className="flex items-center gap-3 text-[10px] text-zinc-400">
        <span>{sb.scene_count} scenes</span>
        <span>{sb.image_count} images</span>
        {sb.updated_at && <span>{format(new Date(sb.updated_at), "yyyy.MM.dd")}</span>}
        {sb.group_id && !filterGroupId && (() => {
          const gIdx = groups.findIndex((g) => g.id === sb.group_id);
          if (gIdx === -1) return null;
          const c = GROUP_COLORS[gIdx % GROUP_COLORS.length];
          return (
            <span className={`ml-auto rounded-full px-1.5 py-0.5 text-[9px] font-medium ${c.pill}`}>
              {groups[gIdx].name}
            </span>
          );
        })()}
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 text-zinc-300 hover:text-red-400 transition text-xs"
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
    } catch { }
  }, []);

  if (!hasDraft) return null;

  return (
    <div
      onClick={onClick}
      className="flex flex-col gap-2 rounded-2xl border-2 border-dashed border-zinc-300 bg-zinc-50 p-4 cursor-pointer hover:border-zinc-400 transition"
    >
      <span className="text-xs font-semibold text-zinc-600">Continue Draft</span>
      <span className="text-[10px] text-zinc-400">Resume your unsaved work</span>
    </div>
  );
}
