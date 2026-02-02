"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { format } from "date-fns";
import { API_BASE } from "./constants";
import type { Character, Tag, LoRA } from "./types";
import { useCharacters } from "./hooks/useCharacters";
import { useProjectGroups } from "./hooks/useProjectGroups";
import { ProjectDropdown, ProjectFormModal, GroupFormModal } from "./components/context";
import { createProject } from "./store/actions/projectActions";
import { createGroup, updateGroup } from "./store/actions/groupActions";
import CharacterEditModal from "./components/shared/CharacterEditModal";
import LoadingSpinner from "./components/ui/LoadingSpinner";
import Toast from "./components/ui/Toast";
import Footer from "./components/ui/Footer";
import ImagePreviewModal from "./components/ui/ImagePreviewModal";
import CommandPalette from "./components/ui/CommandPalette";

const GROUP_COLORS = [
  { pill: "bg-sky-100 text-sky-700", active: "bg-sky-600 text-white", dot: "bg-sky-400" },
  { pill: "bg-emerald-100 text-emerald-700", active: "bg-emerald-600 text-white", dot: "bg-emerald-400" },
  { pill: "bg-amber-100 text-amber-700", active: "bg-amber-600 text-white", dot: "bg-amber-400" },
  { pill: "bg-rose-100 text-rose-700", active: "bg-rose-600 text-white", dot: "bg-rose-400" },
  { pill: "bg-violet-100 text-violet-700", active: "bg-violet-600 text-white", dot: "bg-violet-400" },
  { pill: "bg-teal-100 text-teal-700", active: "bg-teal-600 text-white", dot: "bg-teal-400" },
];

type HomeTab = "storyboards" | "characters";

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

export default function Home() {
  const router = useRouter();
  const [tab, setTab] = useState<HomeTab>("storyboards");

  // Project & Group context
  const { projectId, groupId, projects, groups, selectProject, selectGroup } = useProjectGroups();
  const [filterGroupId, setFilterGroupId] = useState<number | null>(null);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState<(typeof groups)[number] | null>(null);
  // Storyboard list
  const [storyboards, setStoryboards] = useState<StoryboardItem[]>([]);
  const [sbLoading, setSbLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Characters (scoped to current project)
  const { characters, reload: refreshCharacters } = useCharacters();
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [allLoras, setAllLoras] = useState<LoRA[]>([]);
  const [editingCharacter, setEditingCharacter] = useState<Character | undefined>(undefined);
  const [showCharacterModal, setShowCharacterModal] = useState(false);
  const [characterImagePreview, setCharacterImagePreview] = useState<string | null>(null);

  const showToast = useCallback((message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // Reset group filter when project changes
  useEffect(() => {
    setFilterGroupId(null);
  }, [projectId]);

  // Fetch storyboards (filtered by project + optional group)
  useEffect(() => {
    if (projectId === null) return;
    async function load() {
      setSbLoading(true);
      try {
        const params: Record<string, unknown> = { project_id: projectId };
        if (filterGroupId) params.group_id = filterGroupId;
        const res = await axios.get(`${API_BASE}/storyboards`, { params });
        setStoryboards(res.data);
      } catch {
        showToast("Failed to load storyboards", "error");
      } finally {
        setSbLoading(false);
      }
    }
    load();
  }, [showToast, projectId, filterGroupId]);

  // Fetch tags & loras for character modal
  useEffect(() => {
    if (tab !== "characters") return;
    Promise.all([
      axios.get(`${API_BASE}/tags`).then((r) => setAllTags(r.data)),
      axios.get(`${API_BASE}/loras`).then((r) => setAllLoras(r.data)),
    ]).catch(() => { });
  }, [tab]);

  const handleDeleteStoryboard = async (id: number) => {
    if (!confirm("Delete this storyboard?")) return;
    try {
      await axios.delete(`${API_BASE}/storyboards/${id}`);
      setStoryboards((prev) => prev.filter((s) => s.id !== id));
      showToast("Storyboard deleted", "success");
    } catch {
      showToast("Failed to delete", "error");
    }
  };

  const handleSaveCharacter = async (data: Partial<Character>, id?: number) => {
    if (id) {
      await axios.put(`${API_BASE}/characters/${id}`, data);
    } else {
      await axios.post(`${API_BASE}/characters`, data);
    }
    refreshCharacters();
  };

  const handleDeleteCharacter = async (id: number) => {
    if (!confirm("Delete this character?")) return;
    try {
      await axios.delete(`${API_BASE}/characters/${id}`);
      refreshCharacters();
      showToast("Character deleted", "success");
    } catch {
      showToast("Failed to delete character", "error");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-50 via-white to-zinc-100 font-[family-name:var(--font-sans)]">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-zinc-200/60 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight text-zinc-900">
              Shorts Producer
            </h1>
            <span className="text-zinc-300">/</span>
            <ProjectDropdown
              projects={projects}
              currentId={projectId}
              onSelect={selectProject}
              onNew={() => setShowProjectModal(true)}
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              data-testid="manage-link"
              onClick={() => router.push("/manage")}
              className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-50 transition"
            >
              Manage
            </button>
          </div>
        </div>
      </header>

      {/* Tab Bar */}
      <div className="mx-auto max-w-5xl px-6 pt-4">
        <div className="flex gap-1 rounded-xl bg-zinc-100/60 p-1">
          {(["storyboards", "characters"] as HomeTab[]).map((t) => (
            <button
              key={t}
              data-testid={`home-tab-${t}`}
              onClick={() => setTab(t)}
              className={`flex-1 rounded-lg py-2 text-xs font-semibold transition ${tab === t
                ? "bg-white text-zinc-900 shadow-sm"
                : "text-zinc-500 hover:text-zinc-700"
                }`}
            >
              {t === "storyboards" ? "Storyboards" : "Characters"}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="mx-auto max-w-5xl px-6 py-6">
        {tab === "storyboards" && (
          <section>
            {/* Group filter pills */}
            <div className="mb-4 flex items-center gap-1.5 overflow-x-auto">
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
              {(filterGroupId || groups.length === 1) && (
                <button
                  onClick={() => {
                    selectGroup(filterGroupId ?? groups[0].id);
                    router.push("/studio?new=true");
                  }}
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
                  onClick={() => {
                    if (groups.length === 0) {
                      setShowGroupModal(true);
                    } else {
                      selectGroup(filterGroupId ?? groups[0].id);
                      router.push("/studio?new=true");
                    }
                  }}
                  className="rounded-full bg-zinc-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-zinc-800 transition"
                >
                  {groups.length === 0 ? "+ Create Group" : "+ New Storyboard"}
                </button>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {/* Draft card (if exists in localStorage) */}
                <DraftCard onClick={() => router.push("/studio")} />

                {storyboards.map((sb) => (
                  <div
                    key={sb.id}
                    data-testid={`storyboard-card-${sb.id}`}
                    className="group relative flex flex-col gap-2 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm hover:shadow-md transition cursor-pointer"
                    onClick={() => router.push(`/studio?id=${sb.id}`)}
                  >
                    <h3 className="text-sm font-semibold text-zinc-900 line-clamp-1">
                      {sb.title}
                    </h3>
                    {sb.description && (
                      <p className="text-xs text-zinc-500 line-clamp-2">{sb.description}</p>
                    )}
                    <div className="flex items-center gap-3 text-[10px] text-zinc-400">
                      <span>{sb.scene_count} scenes</span>
                      <span>{sb.image_count} images</span>
                      {sb.updated_at && (
                        <span>{format(new Date(sb.updated_at), "yyyy.MM.dd")}</span>
                      )}
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
                      onClick={(e) => { e.stopPropagation(); handleDeleteStoryboard(sb.id); }}
                      className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 text-zinc-300 hover:text-red-400 transition text-xs"
                      title="Delete"
                    >
                      x
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {tab === "characters" && (
          <section>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-bold text-zinc-700">Characters ({characters.length})</h2>
              <button
                onClick={() => { setEditingCharacter(undefined); setShowCharacterModal(true); }}
                className="rounded-full bg-zinc-900 px-4 py-2 text-xs font-semibold text-white hover:bg-zinc-800"
              >
                + New Character
              </button>
            </div>

            {characters.length === 0 ? (
              <div className="flex flex-col items-center gap-4 py-16 text-center">
                <svg className="h-12 w-12 text-zinc-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-zinc-500">No characters yet</p>
                  <p className="mt-1 text-xs text-zinc-400">Characters maintain visual consistency across scenes</p>
                </div>
                <button
                  onClick={() => { setEditingCharacter(undefined); setShowCharacterModal(true); }}
                  className="rounded-full bg-zinc-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-zinc-800 transition"
                >
                  + New Character
                </button>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {characters.map((ch) => (
                  <div
                    key={ch.id}
                    className="group relative flex items-start gap-3 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm hover:shadow-md transition"
                  >
                    {ch.preview_image_url ? (
                      <img
                        src={ch.preview_image_url.startsWith('http') ? ch.preview_image_url : `${API_BASE}${ch.preview_image_url}`}
                        alt={ch.name}
                        onClick={() => { setEditingCharacter(ch); setShowCharacterModal(true); }}
                        className="h-14 w-14 rounded-xl object-cover object-top bg-zinc-100 cursor-pointer hover:ring-2 hover:ring-zinc-300 transition-all"
                      />
                    ) : (
                      <div
                        onClick={() => { setEditingCharacter(ch); setShowCharacterModal(true); }}
                        className="flex h-14 w-14 items-center justify-center rounded-xl bg-zinc-100 text-lg font-bold text-zinc-400 cursor-pointer hover:ring-2 hover:ring-zinc-300 transition-all"
                      >
                        {ch.name.charAt(0)}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-semibold text-zinc-900">{ch.name}</h3>
                      <p className="text-xs text-zinc-500 line-clamp-1">{ch.description || ch.gender}</p>
                      <div className="mt-1 flex gap-1">
                        <button
                          onClick={() => { setEditingCharacter(ch); setShowCharacterModal(true); }}
                          className="text-[10px] text-zinc-500 hover:text-zinc-700 underline"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteCharacter(ch.id)}
                          className="text-[10px] text-zinc-400 hover:text-red-500 underline"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      <Footer />

      {/* Character Edit Modal */}
      {showCharacterModal && (
        <CharacterEditModal
          character={editingCharacter}
          allTags={allTags}
          allLoras={allLoras}
          onClose={() => setShowCharacterModal(false)}
          onSave={handleSaveCharacter}
        />
      )}

      {/* Character Image Preview Modal */}
      {characterImagePreview && (
        <ImagePreviewModal
          src={characterImagePreview}
          onClose={() => setCharacterImagePreview(null)}
        />
      )}

      {toast && <Toast message={toast.message} type={toast.type} />}

      {/* Project Create Modal */}
      {showProjectModal && (
        <ProjectFormModal
          onSave={async (data) => {
            const p = await createProject(data);
            if (p) selectProject(p.id);
          }}
          onClose={() => setShowProjectModal(false)}
        />
      )}

      {/* Group Create Modal */}
      {showGroupModal && projectId && (
        <GroupFormModal
          projectId={projectId}
          onSave={async (data) => {
            const g = await createGroup(data as Parameters<typeof createGroup>[0]);
            if (g) {
              selectGroup(g.id);
              // 그룹 없어서 모달 띄운 경우 → 생성 후 studio로 이동
              if (groups.length === 0) {
                router.push("/studio?new=true");
              }
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
          onSave={async (data) => {
            await updateGroup(editingGroup.id, data);
          }}
          onClose={() => setEditingGroup(null)}
        />
      )}

      <CommandPalette />
    </div>
  );
}

/** Shows a card for the current draft (if one exists in localStorage). */
function DraftCard({ onClick }: { onClick: () => void }) {
  const [hasDraft, setHasDraft] = useState(false);

  useEffect(() => {
    try {
      const stored =
        localStorage.getItem("shorts-producer:studio:v1") ||
        localStorage.getItem("shorts-producer:draft:v1");
      if (stored) {
        const data = JSON.parse(stored);
        // Check if there's meaningful content
        const state = data?.state || data;
        if (state?.topic || (state?.scenes && state.scenes.length > 0)) {
          setHasDraft(true);
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
