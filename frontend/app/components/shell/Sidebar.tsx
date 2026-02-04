"use client";

import { type ReactNode, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import {
  Clapperboard,
  ChevronLeft,
  ChevronRight,
  Plus,
  FolderOpen,
  Settings,
  Trash2,
} from "lucide-react";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import { useStudioStore } from "../../store/useStudioStore";
import { updateProject } from "../../store/actions/projectActions";
import { API_BASE } from "../../constants";
import { cx, LABEL_CLASSES } from "../ui/variants";
import { GroupConfigEditor, ProjectDropdown, ProjectFormModal } from "../context";

type StoryboardItem = { id: number; title: string; group_id: number };

const STORAGE_KEY = "sidebarCollapsed";

// -- Sub-components ----------------------------------------------------------

function SectionHeader({
  label,
  collapsed,
  badge,
}: {
  label: string;
  collapsed: boolean;
  badge?: ReactNode;
}) {
  if (collapsed) return null;
  return (
    <h3 className={cx(LABEL_CLASSES, "flex items-center gap-2 px-3 pt-4 pb-1")}>
      {label}
      {badge}
    </h3>
  );
}

function GroupList({
  groups,
  activeId,
  collapsed,
  onSelect,
  onConfig,
}: {
  groups: { id: number; name: string }[];
  activeId: number | null;
  collapsed: boolean;
  onSelect: (id: number) => void;
  onConfig: (id: number) => void;
}) {
  return (
    <ul className="space-y-0.5 px-1">
      {groups.map((g) => (
        <li key={g.id} className="group/item">
          <div
            className={cx(
              "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition",
              g.id === activeId
                ? "bg-zinc-100 font-medium text-zinc-900"
                : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700"
            )}
          >
            <button
              onClick={() => onSelect(g.id)}
              title={collapsed ? g.name : undefined}
              className="flex min-w-0 flex-1 items-center gap-2"
            >
              <FolderOpen className="h-3.5 w-3.5 shrink-0" />
              {!collapsed && <span className="truncate">{g.name}</span>}
            </button>
            {!collapsed && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onConfig(g.id);
                }}
                title="Group settings"
                className="hidden shrink-0 rounded p-0.5 text-zinc-300 transition group-hover/item:block hover:text-zinc-600"
              >
                <Settings className="h-3 w-3" />
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

function StoryList({
  storyboards,
  activeId,
  collapsed,
  locked,
  onSelect,
  onDelete,
}: {
  storyboards: StoryboardItem[];
  activeId: number | null;
  collapsed: boolean;
  locked: boolean;
  onSelect: (sb: StoryboardItem) => void;
  onDelete: (id: number) => void;
}) {
  if (storyboards.length === 0 && !collapsed) {
    return <p className="px-3 py-1 text-[11px] text-zinc-300">No stories yet</p>;
  }
  return (
    <ul className="space-y-0.5 px-1">
      {storyboards.map((sb) => {
        const isActive = sb.id === activeId;
        const isDisabled = locked && !isActive;
        return (
          <li key={sb.id} className="group/story">
            <div
              className={cx(
                "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition",
                isActive
                  ? "bg-zinc-100 font-medium text-zinc-900"
                  : isDisabled
                    ? "cursor-not-allowed text-zinc-300"
                    : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700"
              )}
            >
              <button
                onClick={() => onSelect(sb)}
                disabled={isDisabled}
                title={
                  isDisabled
                    ? "Autopilot running — wait for completion"
                    : collapsed
                      ? sb.title
                      : undefined
                }
                className="flex min-w-0 flex-1 items-center gap-2"
              >
                <Clapperboard className={cx("h-3.5 w-3.5 shrink-0", isDisabled && "opacity-40")} />
                {!collapsed && <span className="truncate">{sb.title || `Story #${sb.id}`}</span>}
              </button>
              {!collapsed && !locked && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(sb.id);
                  }}
                  title="Delete storyboard"
                  className="hidden shrink-0 rounded p-0.5 text-zinc-300 transition group-hover/story:block hover:text-rose-500"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function AddButton({
  label,
  collapsed,
  onClick,
}: {
  label: string;
  collapsed: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={collapsed ? label : undefined}
      className="mx-1 flex w-[calc(100%-0.5rem)] items-center gap-1.5 rounded-lg px-2 py-1 text-[11px] text-zinc-400 transition hover:bg-zinc-50 hover:text-zinc-600"
    >
      <Plus className="h-3 w-3 shrink-0" />
      {!collapsed && label}
    </button>
  );
}

// -- Main component ----------------------------------------------------------

export default function Sidebar() {
  const router = useRouter();
  const { projectId, groupId, projects, groups, selectProject, selectGroup } = useProjectGroups();
  const storyboardId = useStudioStore((s) => s.storyboardId);
  const setMeta = useStudioStore((s) => s.setMeta);
  const isAutoRunning = useStudioStore((s) => s.isAutoRunning);
  const showToast = useStudioStore((s) => s.showToast);

  const [collapsed, setCollapsed] = useState(false);
  const [storyboards, setStoryboards] = useState<StoryboardItem[]>([]);
  const [configGroupId, setConfigGroupId] = useState<number | null>(null);
  const [showProjectSettings, setShowProjectSettings] = useState(false);

  // Hydrate collapse state from localStorage (client only)
  useEffect(() => {
    setCollapsed(localStorage.getItem(STORAGE_KEY) === "true");
  }, []);

  // Persist collapse state
  const toggleCollapse = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  // Fetch storyboards when selected group changes
  useEffect(() => {
    if (!groupId) {
      setStoryboards([]);
      return;
    }
    axios
      .get<StoryboardItem[]>(`${API_BASE}/storyboards`, { params: { group_id: groupId } })
      .then((r) => setStoryboards(r.data))
      .catch(() => setStoryboards([]));
  }, [groupId]);

  const warnAutoRunning = useCallback(() => {
    showToast("Autopilot running — wait for completion", "warning");
  }, [showToast]);

  const handleStorySelect = useCallback(
    (sb: StoryboardItem) => {
      if (isAutoRunning && sb.id !== storyboardId) {
        warnAutoRunning();
        return;
      }
      setMeta({ storyboardId: sb.id, storyboardTitle: sb.title });
      router.push(`/studio?id=${sb.id}`);
    },
    [setMeta, router, isAutoRunning, storyboardId, warnAutoRunning]
  );

  const handleGroupSelect = useCallback(
    (id: number) => {
      if (isAutoRunning) {
        warnAutoRunning();
        return;
      }
      selectGroup(id);
    },
    [selectGroup, isAutoRunning, warnAutoRunning]
  );

  const handleNewStory = useCallback(() => {
    if (isAutoRunning) {
      warnAutoRunning();
      return;
    }
    router.push("/studio?new=true");
  }, [router, isAutoRunning, warnAutoRunning]);

  const handleStoryDelete = useCallback(
    async (id: number) => {
      if (!confirm("Delete this storyboard?")) return;
      try {
        await axios.delete(`${API_BASE}/storyboards/${id}`);
        setStoryboards((prev) => prev.filter((s) => s.id !== id));
        if (storyboardId === id) {
          setMeta({ storyboardId: null, storyboardTitle: "" });
          router.push("/studio?new=true");
        }
        showToast("Storyboard deleted", "success");
      } catch {
        showToast("Failed to delete", "error");
      }
    },
    [storyboardId, setMeta, router, showToast]
  );

  const sidebarWidth = collapsed ? "w-16" : "w-64";

  return (
    <>
      <aside
        className={cx(
          "hidden flex-col border-r border-zinc-200 bg-white transition-[width] duration-200 lg:flex",
          sidebarWidth
        )}
      >
        {/* Project Selector */}
        {!collapsed && (
          <div className="border-b border-zinc-100 px-3 py-3">
            <div className="flex items-center gap-1">
              <ProjectDropdown
                projects={projects}
                currentId={projectId}
                onSelect={selectProject}
                onNew={() => setShowProjectSettings(true)}
              />
              <button
                onClick={() => setShowProjectSettings(true)}
                title="Project settings"
                className="ml-auto shrink-0 rounded p-1 text-zinc-300 transition hover:bg-zinc-100 hover:text-zinc-600"
              >
                <Settings className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto">
          {/* Groups */}
          <SectionHeader label="Groups" collapsed={collapsed} />
          <GroupList
            groups={groups}
            activeId={groupId}
            collapsed={collapsed}
            onSelect={handleGroupSelect}
            onConfig={setConfigGroupId}
          />
          <AddButton
            label="New Group"
            collapsed={collapsed}
            onClick={() => router.push("/manage?tab=groups")}
          />

          {/* Divider */}
          <div className="mx-3 my-2 border-t border-zinc-100" />

          {/* Stories */}
          <SectionHeader
            label="Stories"
            collapsed={collapsed}
            badge={
              isAutoRunning ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900 px-1.5 py-0.5 text-[9px] font-semibold tracking-wider text-white uppercase">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                  Running
                </span>
              ) : null
            }
          />
          <StoryList
            storyboards={storyboards}
            activeId={storyboardId}
            collapsed={collapsed}
            locked={isAutoRunning}
            onSelect={handleStorySelect}
            onDelete={handleStoryDelete}
          />
          <AddButton label="New Story" collapsed={collapsed} onClick={handleNewStory} />
        </div>

        {/* Collapse Toggle */}
        <button
          onClick={toggleCollapse}
          className="flex items-center justify-center border-t border-zinc-100 py-2 text-zinc-400 transition hover:text-zinc-600"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </aside>

      {configGroupId && (
        <GroupConfigEditor groupId={configGroupId} onClose={() => setConfigGroupId(null)} />
      )}

      {showProjectSettings && projectId && (
        <ProjectFormModal
          project={projects.find((p) => p.id === projectId)}
          onSave={async (data) => {
            await updateProject(projectId, data);
          }}
          onClose={() => setShowProjectSettings(false)}
        />
      )}
    </>
  );
}
