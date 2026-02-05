"use client";

import { useState, useEffect, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Settings } from "lucide-react";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import { useStudioStore } from "../../store/useStudioStore";
import { createGroup, deleteGroup } from "../../store/actions/groupActions";
import { deleteProject, updateProject } from "../../store/actions/projectActions";
import { cx } from "../ui/variants";
import {
  GroupConfigEditor,
  GroupDropdown,
  GroupFormModal,
  ProjectDropdown,
  ProjectFormModal,
} from "../context";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";
import SectionHeader from "./sidebar/SectionHeader";
import StudioSections from "./sidebar/StudioSections";

const STORAGE_KEY = "sidebarCollapsed";

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const isStudio = pathname.startsWith("/studio");

  const { projectId, groupId, projects, groups, selectProject, selectGroup } = useProjectGroups();
  const isAutoRunning = useStudioStore((s) => s.isAutoRunning);
  const showToast = useStudioStore((s) => s.showToast);
  const setMeta = useStudioStore((s) => s.setMeta);
  const resetScenes = useStudioStore((s) => s.resetScenes);
  const { confirm, dialogProps } = useConfirm();

  const [collapsed, setCollapsed] = useState(false);
  const [configGroupId, setConfigGroupId] = useState<number | null>(null);
  const [showProjectSettings, setShowProjectSettings] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);

  // Hydrate collapse state from localStorage (client only)
  useEffect(() => {
    setCollapsed(localStorage.getItem(STORAGE_KEY) === "true");
  }, []);

  const toggleCollapse = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  const warnAutoRunning = useCallback(() => {
    showToast("Autopilot running — wait for completion", "warning");
  }, [showToast]);

  const handleDeleteProject = useCallback(
    async (project: { id: number; name: string }) => {
      const ok = await confirm({
        title: "Delete Project",
        message: `Delete "${project.name}"? This cannot be undone.`,
        confirmLabel: "Delete",
        variant: "danger",
      });
      if (!ok) return;
      const deleted = await deleteProject(project.id);
      if (deleted && project.id === projectId) {
        setMeta({ projectId: null, groupId: null, storyboardId: null, storyboardTitle: "" });
        resetScenes();
      }
    },
    [confirm, projectId, setMeta, resetScenes]
  );

  const handleDeleteGroup = useCallback(
    async (id: number) => {
      const group = groups.find((g) => g.id === id);
      const ok = await confirm({
        title: "Delete Group",
        message: `Delete "${group?.name ?? "this group"}"? This cannot be undone.`,
        confirmLabel: "Delete",
        variant: "danger",
      });
      if (!ok) return;
      const deleted = await deleteGroup(id);
      if (deleted && id === groupId) {
        setMeta({ groupId: null, storyboardId: null, storyboardTitle: "" });
        resetScenes();
      }
    },
    [confirm, groups, groupId, setMeta, resetScenes]
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
          <div className="border-b border-zinc-100 pb-3">
            <SectionHeader label="Project" collapsed={collapsed} />
            <div className="flex items-center gap-1 px-1">
              <ProjectDropdown
                projects={projects}
                currentId={projectId}
                onSelect={(id) => {
                  selectProject(id);
                  if (isStudio) router.push("/");
                }}
                onNew={() => setShowProjectSettings(true)}
                onDelete={handleDeleteProject}
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
          {/* Group Selector */}
          <div className="border-b border-zinc-100 pb-3">
            <SectionHeader label="Group" collapsed={collapsed} />
            <div className="flex items-center gap-1 px-1">
              <GroupDropdown
                groups={groups}
                currentId={groupId}
                onSelect={handleGroupSelect}
                onNew={() => setShowGroupModal(true)}
                onEdit={(g) => setConfigGroupId(g.id)}
                onDelete={(g) => handleDeleteGroup(g.id)}
                collapsed={collapsed}
              />
              {!collapsed && (
                <button
                  onClick={() => groupId && setConfigGroupId(groupId)}
                  title="Group settings"
                  className="ml-auto shrink-0 rounded p-1 text-zinc-300 transition hover:bg-zinc-100 hover:text-zinc-600"
                >
                  <Settings className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Stories — studio only */}
          {isStudio && <StudioSections collapsed={collapsed} groupId={groupId} />}
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

      {showGroupModal && projectId && (
        <GroupFormModal
          projectId={projectId}
          onSave={async (data) => {
            const g = await createGroup(data as Parameters<typeof createGroup>[0]);
            if (g) {
              selectGroup(g.id);
              setConfigGroupId(g.id);
            }
          }}
          onClose={() => setShowGroupModal(false)}
        />
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

      <ConfirmDialog {...dialogProps} />
    </>
  );
}
