"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ChevronRight, Clapperboard, Settings, X } from "lucide-react";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import { useContextStore } from "../../store/useContextStore";
import { useUIStore } from "../../store/useUIStore";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { deleteGroup } from "../../store/actions/groupActions";
import { deleteProject, updateProject } from "../../store/actions/projectActions";
import { ALL_GROUPS_ID } from "../../constants";
import ProjectDropdown from "./ProjectDropdown";
import GroupDropdown from "./GroupDropdown";
import ProjectFormModal from "./ProjectFormModal";
import GroupConfigEditor from "./GroupConfigEditor";
import SetupWizard from "./SetupWizard";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";

export default function PersistentContextBar() {
  const pathname = usePathname();
  const router = useRouter();
  const isStudio = pathname.startsWith("/studio");
  const isHome = pathname === "/";
  const isAssetPage = pathname.startsWith("/library") || pathname.startsWith("/characters/");

  const { projectId, groupId, projects, groups, selectProject, selectGroup } = useProjectGroups();
  const storyboardId = useContextStore((s) => s.storyboardId);
  const storyboardTitle = useContextStore((s) => s.storyboardTitle);
  const setContext = useContextStore((s) => s.setContext);
  const resetContext = useContextStore((s) => s.resetContext);
  const isAutoRunning = useUIStore((s) => s.isAutoRunning);
  const showToast = useUIStore((s) => s.showToast);
  const setScenes = useStoryboardStore((s) => s.setScenes);
  const clearScenes = useCallback(() => setScenes([]), [setScenes]);

  const { confirm, dialogProps } = useConfirm();
  const [configGroupId, setConfigGroupId] = useState<number | null>(null);
  const [projectModalMode, setProjectModalMode] = useState<"edit" | null>(null);
  const showSetupWizard = useUIStore((s) => s.showSetupWizard);
  const setupWizardInitialStep = useUIStore((s) => s.setupWizardInitialStep);
  const setUI = useUIStore((s) => s.set);

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
        setContext({ projectId: null, groupId: null, storyboardId: null, storyboardTitle: "" });
        clearScenes();
      }
    },
    [confirm, projectId, setContext, clearScenes]
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
        setContext({ groupId: null, storyboardId: null, storyboardTitle: "" });
        clearScenes();
      }
    },
    [confirm, groups, groupId, setContext, clearScenes]
  );

  const handleGroupSelect = useCallback(
    (id: number) => {
      if (isAutoRunning) {
        showToast("Autopilot running — wait for completion", "warning");
        return;
      }
      selectGroup(id);
    },
    [selectGroup, isAutoRunning, showToast]
  );

  const hasStoryboard = storyboardId !== null && !isStudio && !isHome && !isAssetPage;

  // Hide context bar on Home page — but still render wizard if triggered
  if (isHome) {
    return showSetupWizard ? (
      <SetupWizard
        initialStep={setupWizardInitialStep}
        onClose={() => setUI({ showSetupWizard: false })}
      />
    ) : null;
  }

  return (
    <>
      <div className="flex h-8 shrink-0 items-center justify-between border-b border-zinc-100 bg-zinc-50/80 px-4 text-xs text-zinc-500">
        <div className="flex items-center gap-0.5 truncate">
          <ProjectDropdown
            projects={projects}
            currentId={projectId}
            onSelect={(id) => {
              selectProject(id);
              if (isStudio) router.push("/");
            }}
            onNew={() => setUI({ showSetupWizard: true, setupWizardInitialStep: 1 })}
            onEdit={() => setProjectModalMode("edit")}
            onDelete={handleDeleteProject}
          />

          <ChevronRight className="h-3 w-3 shrink-0 text-zinc-300" />

          <GroupDropdown
            groups={groups}
            currentId={groupId}
            onSelect={handleGroupSelect}
            onNew={() => setUI({ showSetupWizard: true, setupWizardInitialStep: 2 })}
            onEdit={(g) => setConfigGroupId(g.id)}
            onDelete={(g) => handleDeleteGroup(g.id)}
            showAllOption
          />

          {hasStoryboard && (
            <>
              <ChevronRight className="h-3 w-3 shrink-0 text-zinc-300" />
              <Clapperboard className="ml-1 h-3 w-3 shrink-0 text-zinc-400" />
              <Link
                href={`/studio?id=${storyboardId}`}
                className="ml-1 truncate font-medium text-zinc-700 hover:text-zinc-900 hover:underline"
              >
                {storyboardTitle || "Untitled"}
              </Link>
            </>
          )}
        </div>

        <div className="flex items-center gap-1">
          {groupId !== null && groupId !== ALL_GROUPS_ID && (
            <button
              onClick={() => setConfigGroupId(groupId)}
              title="Group settings"
              className="shrink-0 rounded p-0.5 text-zinc-400 transition hover:bg-zinc-200 hover:text-zinc-600"
            >
              <Settings className="h-3 w-3" />
            </button>
          )}
          {hasStoryboard && (
            <button
              onClick={resetContext}
              className="shrink-0 rounded p-0.5 text-zinc-400 transition hover:bg-zinc-200 hover:text-zinc-600"
              title="Dismiss storyboard context"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>

      {configGroupId && (
        <GroupConfigEditor groupId={configGroupId} onClose={() => setConfigGroupId(null)} />
      )}

      {projectModalMode === "edit" && projectId && (
        <ProjectFormModal
          project={projects.find((p) => p.id === projectId)}
          onSave={async (data) => {
            await updateProject(projectId, data);
          }}
          onClose={() => setProjectModalMode(null)}
        />
      )}

      {showSetupWizard && (
        <SetupWizard
          initialStep={setupWizardInitialStep}
          existingProjectId={setupWizardInitialStep === 2 ? (projectId ?? undefined) : undefined}
          onClose={() => setUI({ showSetupWizard: false })}
        />
      )}

      <ConfirmDialog {...dialogProps} />
    </>
  );
}
