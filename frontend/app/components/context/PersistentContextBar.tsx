"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ChevronRight, Clapperboard, Settings, X } from "lucide-react";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import { useContextStore } from "../../store/useContextStore";
import { useUIStore } from "../../store/useUIStore";
import { deleteGroup } from "../../store/actions/groupActions";
import { deleteProject, updateProject } from "../../store/actions/projectActions";
import { cancelPendingSave } from "../../store/effects/autoSave";
import { resetTransientStores } from "../../store/resetAllStores";
import { clearStudioUrlParams } from "../../utils/url";
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
  const { projectId, groupId, projects, groups, selectProject, selectGroup } = useProjectGroups();
  const storyboardId = useContextStore((s) => s.storyboardId);
  const storyboardTitle = useContextStore((s) => s.storyboardTitle);
  const setContext = useContextStore((s) => s.setContext);
  const resetContext = useContextStore((s) => s.resetContext);
  const isAutoRunning = useUIStore((s) => s.isAutoRunning);
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();
  const configGroupId = useUIStore((s) => s.configGroupId);
  const [projectModalMode, setProjectModalMode] = useState<"edit" | null>(null);
  const showSetupWizard = useUIStore((s) => s.showSetupWizard);
  const setupWizardInitialStep = useUIStore((s) => s.setupWizardInitialStep);
  const setUI = useUIStore((s) => s.set);

  const handleDeleteProject = useCallback(
    async (project: { id: number; name: string }) => {
      const ok = await confirm({
        title: "채널 삭제",
        message: (
          <>
            <span className="font-semibold text-zinc-900">{project.name}</span>을(를)
            삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.
          </>
        ),
        confirmLabel: "삭제",
        variant: "danger",
      });
      if (!ok) return;
      const deleted = await deleteProject(project.id);
      if (deleted && project.id === projectId) {
        cancelPendingSave();
        setContext({ projectId: null, groupId: null, storyboardId: null, storyboardTitle: "" });
        resetTransientStores();
        clearStudioUrlParams();
      }
    },
    [confirm, projectId, setContext]
  );

  const handleDeleteGroup = useCallback(
    async (id: number) => {
      const group = groups.find((g) => g.id === id);
      const ok = await confirm({
        title: "시리즈 삭제",
        message: (
          <>
            <span className="font-semibold text-zinc-900">{group?.name ?? "this group"}</span>
            을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.
          </>
        ),
        confirmLabel: "삭제",
        variant: "danger",
      });
      if (!ok) return;
      const deleted = await deleteGroup(id);
      if (deleted && id === groupId) {
        cancelPendingSave();
        setContext({ groupId: null, storyboardId: null, storyboardTitle: "" });
        resetTransientStores();
        clearStudioUrlParams();
      }
    },
    [confirm, groups, groupId, setContext]
  );

  const handleGroupSelect = useCallback(
    (id: number) => {
      if (isAutoRunning) {
        showToast("Auto Run 실행 중 — 완료될 때까지 기다려주세요", "warning");
        return;
      }
      selectGroup(id);
      if (isStudio) router.replace("/studio");
    },
    [selectGroup, isAutoRunning, showToast, isStudio, router]
  );

  const handleDismiss = useCallback(() => {
    cancelPendingSave();
    resetContext();
    resetTransientStores();
    // router.replace만 사용 — clearStudioUrlParams(replaceState)와의 경쟁 조건 방지
    // replaceState는 Next.js useSearchParams를 업데이트하지 않아 stale ?id= 재로드 발생
    if (isStudio) router.replace("/studio");
  }, [resetContext, isStudio, router]);

  const hasStoryboard = storyboardId !== null && !isHome;

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
      <div className="flex h-8 shrink-0 items-center justify-between border-b border-zinc-100 bg-zinc-50/80 px-8 text-xs text-zinc-500">
        <div className="flex items-center gap-0.5 truncate">
          <ProjectDropdown
            projects={projects}
            currentId={projectId}
            onSelect={(id) => {
              selectProject(id);
              if (isStudio) router.replace("/studio");
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
            onEdit={(g) => setUI({ configGroupId: g.id })}
            onDelete={(g) => handleDeleteGroup(g.id)}
            showAllOption
          />

          {hasStoryboard && (
            <>
              <ChevronRight className="h-3 w-3 shrink-0 text-zinc-300" />
              <Clapperboard className="ml-1 h-3 w-3 shrink-0 text-zinc-400" />
              {isStudio ? (
                <span className="ml-1 truncate font-medium text-zinc-700">
                  {storyboardTitle || "Untitled"}
                </span>
              ) : (
                <Link
                  href={`/studio?id=${storyboardId}`}
                  className="ml-1 truncate font-medium text-zinc-700 hover:text-zinc-900 hover:underline"
                >
                  {storyboardTitle || "Untitled"}
                </Link>
              )}
            </>
          )}
        </div>

        <div className="flex items-center gap-1">
          {groupId !== null && groupId !== ALL_GROUPS_ID && (
            <button
              onClick={() => setUI({ configGroupId: groupId })}
              title="시리즈 설정"
              className="shrink-0 rounded p-0.5 text-zinc-400 transition hover:bg-zinc-200 hover:text-zinc-600"
            >
              <Settings className="h-3 w-3" />
            </button>
          )}
          {hasStoryboard && (
            <button
              onClick={handleDismiss}
              className="shrink-0 rounded p-0.5 text-zinc-400 transition hover:bg-zinc-200 hover:text-zinc-600"
              title="Dismiss storyboard context"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>

      {configGroupId && (
        <GroupConfigEditor groupId={configGroupId} onClose={() => setUI({ configGroupId: null })} />
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
