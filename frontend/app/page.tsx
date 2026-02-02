"use client";

import { useEffect, useState, useCallback, useRef } from "react";
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
import Popover from "./components/ui/Popover";

type HomeTab = "storyboards" | "characters";

interface StoryboardItem {
  id: number;
  title: string;
  description: string | null;
  scene_count: number;
  image_count: number;
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
  const [showGroupPicker, setShowGroupPicker] = useState(false);
  const newSbBtnRef = useRef<HTMLButtonElement>(null);

  // Storyboard list
  const [storyboards, setStoryboards] = useState<StoryboardItem[]>([]);
  const [sbLoading, setSbLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Characters (scoped to current project)
  const { characters, reload: refreshCharacters } = useCharacters(projectId);
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
      await axios.post(`${API_BASE}/characters`, { ...data, project_id: projectId });
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
              ref={newSbBtnRef}
              data-testid="new-storyboard-btn"
              onClick={() => {
                if (groups.length === 0) {
                  setShowGroupModal(true);
                } else if (filterGroupId || groups.length === 1) {
                  selectGroup(filterGroupId ?? groups[0].id);
                  router.push("/studio?new=true");
                } else {
                  setShowGroupPicker(true);
                }
              }}
              className="rounded-full bg-zinc-900 px-4 py-2 text-xs font-semibold text-white hover:bg-zinc-800 transition"
            >
              + New Storyboard
            </button>
            <Popover anchorRef={newSbBtnRef} open={showGroupPicker} onClose={() => setShowGroupPicker(false)}>
              <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Select Group</p>
              {groups.map((g) => (
                <button
                  key={g.id}
                  onClick={() => {
                    selectGroup(g.id);
                    setShowGroupPicker(false);
                    router.push("/studio?new=true");
                  }}
                  className="flex w-full items-center px-3 py-2 text-left text-xs text-zinc-700 hover:bg-zinc-50 transition"
                >
                  {g.name}
                </button>
              ))}
            </Popover>
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
              {groups.map((g) => (
                <span key={g.id} className="group/pill relative shrink-0">
                  <button
                    onClick={() => { setFilterGroupId(g.id); selectGroup(g.id); }}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                      filterGroupId === g.id
                        ? "bg-zinc-900 text-white"
                        : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
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
              ))}
              <button
                onClick={() => setShowGroupModal(true)}
                className="shrink-0 rounded-full border border-dashed border-zinc-300 px-3 py-1 text-xs text-zinc-400 hover:border-zinc-400 hover:text-zinc-600 transition"
              >
                + New Group
              </button>
            </div>

            {sbLoading ? (
              <div className="flex justify-center py-12">
                <LoadingSpinner size="md" />
              </div>
            ) : storyboards.length === 0 ? (
              <div className="flex flex-col items-center gap-4 py-16 text-center">
                <p className="text-sm text-zinc-400">No storyboards yet.</p>
                <button
                  onClick={() => router.push("/studio")}
                  className="rounded-full bg-zinc-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-zinc-800"
                >
                  Create Your First
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
              <p className="py-8 text-center text-sm text-zinc-400">No characters yet.</p>
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
