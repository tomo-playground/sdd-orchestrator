"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useRenderStore } from "../../store/useRenderStore";
import { useUIStore } from "../../store/useUIStore";
import { useContextStore } from "../../store/useContextStore";
import StudioWorkspace from "../../components/studio/StudioWorkspace";
import StudioWorkspaceTabs from "../../components/studio/StudioWorkspaceTabs";
import PipelineStatusDots from "../../components/studio/PipelineStatusDots";
import MaterialsPopover from "../../components/studio/MaterialsPopover";
import StudioKanbanView from "../../components/studio/StudioKanbanView";

import LoadingSpinner from "../../components/ui/LoadingSpinner";
import Skeleton from "../../components/ui/Skeleton";
import ImagePreviewModal from "../../components/ui/ImagePreviewModal";
import VideoPreviewModal from "../../components/ui/VideoPreviewModal";
import AutoRunStatus from "../../components/storyboard/AutoRunStatus";
import ResumeConfirmModal from "../../components/storyboard/ResumeConfirmModal";
import StoryboardActionsBar from "../../components/storyboard/StoryboardActionsBar";
import StyleProfileModal from "../../components/setup/StyleProfileModal";
import { ContextBar, GroupFormModal } from "../../components/context";
import { useAutopilot } from "../../hooks/useAutopilot";
import { useAutopilotCheckpoint } from "../../hooks/useAutopilotCheckpoint";
import { useStudioInitialization } from "../../hooks/useStudioInitialization";
import { useCharacterAutoLoad } from "../../hooks/useCharacterAutoLoad";
import { useStudioOnboarding } from "../../hooks/useStudioOnboarding";
import { createGroup } from "../../store/actions/groupActions";
import { SUB_NAV_CLASSES } from "../../components/ui/variants";
import { runAutoRunFromStep } from "../../store/actions/autopilotActions";
import { saveStoryboard, persistStoryboard } from "../../store/actions/storyboardActions";
import { handleStyleProfileComplete } from "../../store/actions/styleProfileActions";
import PreflightModal from "../../components/common/PreflightModal";
import { runPreflight, buildPreflightInput, getStepsToExecute } from "../../utils/preflight";
import type { AutoRunStepId } from "../../utils/preflight";
import { AUTO_RUN_STEPS } from "../../constants";
import { useKeyboardShortcuts } from "../../hooks/useKeyboardShortcuts";
import { initAutoSave } from "../../store/effects/autoSave";

/** AutoRun step → Studio tab mapping (에러 시 관련 탭에서만 상세 패널 표시) */
const STEP_TO_TAB: Record<string, string> = { stage: "stage", images: "direct", render: "publish" };

function StudioContent() {
  const { isLoadingDb, loadedProfileId, storyboardId, needsStyleProfile } =
    useStudioInitialization();
  useCharacterAutoLoad();
  const { showStyleProfileModal, setShowStyleProfileModal } = useStudioOnboarding({
    isLoadingDb,
    storyboardId,
    needsStyleProfile,
    loadedProfileId,
  });

  // Auto-save: isDirty subscribe → 2s debounce → persistStoryboard
  useEffect(() => {
    const cleanup = initAutoSave();
    return cleanup;
  }, []);

  // Routing: URL params (?id=X or ?new=true) determine kanban vs editor
  // contextStoryboardId (localStorage) is NOT used — URL is the single source of truth
  const searchParams = useSearchParams();
  const isNewMode = useUIStore((s) => s.isNewStoryboardMode) || searchParams.get("new") === "true";
  const hasStoryboard = !!storyboardId || isNewMode;

  // Auto-activate Script tab for new storyboards
  const setActiveTab = useUIStore((s) => s.setActiveTab);
  useEffect(() => {
    if (isNewMode) setActiveTab("script");
  }, [isNewMode, setActiveTab]);

  // Store selectors — split stores
  const setUI = useUIStore((s) => s.set);
  const scenes = useStoryboardStore((s) => s.scenes);
  const storyboardTitle = useContextStore((s) => s.storyboardTitle);
  const imagePreviewSrc = useUIStore((s) => s.imagePreviewSrc);
  const imagePreviewCandidates = useUIStore((s) => s.imagePreviewCandidates);
  const videoPreviewSrc = useUIStore((s) => s.videoPreviewSrc);
  const showToast = useUIStore((s) => s.showToast);
  const showPreflightModal = useUIStore((s) => s.showPreflightModal);
  const groups = useContextStore((s) => s.groups);
  const projectId = useContextStore((s) => s.projectId);
  const isRendering = useRenderStore((s) => s.isRendering);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const setContext = useContextStore((s) => s.setContext);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    try {
      await saveStoryboard();
    } finally {
      setIsSaving(false);
    }
  }, []);

  // Autopilot
  const autopilot = useAutopilot();
  const { CKPT_KEY, pendingCheckpoint, setPendingCheckpoint } = useAutopilotCheckpoint(
    storyboardId ? Number(storyboardId) : null,
    autopilot
  );

  const activeTab = useUIStore((s) => s.activeTab);
  const showAutoRun = autopilot.autoRunState.status !== "idle";
  // Error 시 관련 탭에서만 상세 패널 표시 (다른 탭은 SubNav 뱃지만)
  const isAutoRunError = autopilot.autoRunState.status === "error";
  const errorTab = STEP_TO_TAB[autopilot.autoRunState.step];
  const showAutoRunPanel = showAutoRun && (!isAutoRunError || !errorTab || errorTab === activeTab);

  const isAutoRunningRef = useRef(false);
  isAutoRunningRef.current = autopilot.isAutoRunning;
  useEffect(() => {
    if (!isAutoRunningRef.current) {
      autopilot.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storyboardId]);

  // Script → AutoRun chain: pendingAutoRun signal
  const pendingAutoRun = useUIStore((s) => s.pendingAutoRun);
  const scenesReady = useStoryboardStore((s) => s.scenes.length > 0);
  useEffect(() => {
    if (!pendingAutoRun) return;
    // Guard: scenes가 아직 Zustand에 반영되지 않았으면 다음 렌더까지 대기
    // (syncToGlobalStore ↔ setPendingAutoRun 타이밍 경합 방어)
    if (!scenesReady) return;
    useUIStore.getState().setPendingAutoRun(false);
    const preflight = runPreflight(buildPreflightInput());
    if (preflight.errors.length > 0) {
      setUI({ showPreflightModal: true });
    } else {
      const stepsToRun = getStepsToExecute(preflight);
      if (stepsToRun.length > 0) {
        runAutoRunFromStep(stepsToRun[0], autopilot, stepsToRun);
      } else {
        useUIStore.getState().showToast("모든 단계가 이미 완료되었습니다.", "success");
      }
    }
  }, [pendingAutoRun, scenesReady, autopilot, setUI]);

  // Dirty state guard
  const isDirty = useStoryboardStore((s) => s.isDirty);
  const isGenerating = useStoryboardStore((s) => Object.keys(s.imageGenProgress).length > 0);

  // Warn before refresh/close during render, autopilot, unsaved changes, or image generation
  useEffect(() => {
    if (!isRendering && !autopilot.isAutoRunning && !isDirty && !isGenerating) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isRendering, autopilot.isAutoRunning, isDirty, isGenerating]);

  // Keyboard Shortcuts
  useKeyboardShortcuts([
    {
      key: "s",
      metaKey: true,
      ctrlKey: true,
      action: () => {
        if (scenes.length > 0) handleSave();
      },
      preventDefault: true,
    },
    {
      key: "Enter",
      metaKey: true,
      action: () => {
        if (!isRendering && !autopilot.isAutoRunning) {
          setUI({ showPreflightModal: true });
        }
      },
      preventDefault: true,
    },
  ]);

  if (isLoadingDb) {
    return (
      <div className="flex h-[calc(100vh-56px)] flex-col">
        {/* Skeleton sub-nav */}
        <div className="flex h-12 items-center justify-between border-b border-zinc-100 px-8">
          <Skeleton className="h-4 w-40" />
          <div className="flex items-center gap-3">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-32" />
          </div>
          <Skeleton className="h-7 w-24 rounded-lg" />
        </div>
        {/* Skeleton workspace area */}
        <div className="flex flex-1 gap-4 p-8">
          {/* Left panel skeleton */}
          <div className="flex w-72 flex-col gap-3">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-28 w-full rounded-xl" />
            ))}
          </div>
          {/* Main panel skeleton */}
          <div className="flex flex-1 flex-col gap-4">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-64 w-full rounded-xl" />
            <Skeleton className="h-32 w-full rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  // If no storyboard selected, show the Project List (Kanban)
  if (!hasStoryboard) {
    return <StudioKanbanView />;
  }

  // Timeline view: storyboard selected
  return (
    <div className="flex h-[calc(100vh-56px)] flex-col">
      {/* Sub-Nav: 3-zone layout — [Title] | [Pipeline · Materials · Tabs] | [Actions] */}
      <div className={SUB_NAV_CLASSES}>
        <div className="flex items-center justify-between px-8 py-2">
          {/* Left: Title */}
          <ContextBar title={storyboardTitle || "새 영상"} />

          {/* Center: Status + Tabs */}
          <div className="flex items-center gap-3">
            <PipelineStatusDots />
            <div className="h-4 w-px bg-zinc-200" />
            <MaterialsPopover />
            <div className="h-4 w-px bg-zinc-200" />
            <StudioWorkspaceTabs />
          </div>

          {/* Right: Actions */}
          <StoryboardActionsBar
            onAutoRun={() => setUI({ showPreflightModal: true })}
            onSave={handleSave}
            isRendering={isRendering}
            isAutoRunning={autopilot.isAutoRunning}
            isSaving={isSaving}
            autoRunStep={autopilot.autoRunState.step}
            autoRunStatus={autopilot.autoRunState.status}
            showSave={scenes.length > 0}
          />
        </div>
      </div>

      {/* No-group banner — inside flex column, before workspace */}
      {groups.length === 0 && (
        <div className="shrink-0 px-8 pt-3">
          <div className="flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-xs text-amber-800">영상을 저장하려면 시리즈를 만들어야 합니다.</p>
            <button
              onClick={() => setShowGroupModal(true)}
              className="shrink-0 rounded-full bg-amber-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-amber-700"
            >
              + 시리즈 만들기
            </button>
          </div>
        </div>
      )}

      {pendingCheckpoint && (
        <ResumeConfirmModal
          resumeStep={pendingCheckpoint.step}
          timestamp={pendingCheckpoint.timestamp}
          onResume={() => {
            setPendingCheckpoint(null);
            if (CKPT_KEY) localStorage.removeItem(CKPT_KEY);
            const stepIndex = AUTO_RUN_STEPS.findIndex((s) => s.id === pendingCheckpoint.step);
            const stepsFromHere = AUTO_RUN_STEPS.slice(stepIndex).map((s) => s.id as AutoRunStepId);
            runAutoRunFromStep(pendingCheckpoint.step, autopilot, stepsFromHere);
          }}
          onStartFresh={() => {
            setPendingCheckpoint(null);
            if (CKPT_KEY) localStorage.removeItem(CKPT_KEY);
            const preflight = runPreflight(buildPreflightInput());
            const stepsToRun = getStepsToExecute(preflight);
            const start = stepsToRun[0] ?? "stage";
            runAutoRunFromStep(start, autopilot, stepsToRun.length > 0 ? stepsToRun : undefined);
          }}
          onDismiss={() => {
            setPendingCheckpoint(null);
            if (CKPT_KEY) localStorage.removeItem(CKPT_KEY);
          }}
        />
      )}

      {/* AutoRun Status — 에러 시 관련 탭에서만, 그 외는 모든 탭에서 표시 */}
      {showAutoRunPanel && (
        <div className="shrink-0 px-8 pt-3">
          <AutoRunStatus
            autoRunState={autopilot.autoRunState}
            autoRunLog={autopilot.autoRunLog}
            autoRunProgress={autopilot.autoRunProgress}
            storyboardTitle={storyboardTitle || undefined}
            onResume={(step) => {
              const stepIndex = AUTO_RUN_STEPS.findIndex((s) => s.id === step);
              const stepsFromHere = AUTO_RUN_STEPS.slice(stepIndex).map(
                (s) => s.id as AutoRunStepId
              );
              runAutoRunFromStep(step, autopilot, stepsFromHere);
            }}
            onRestart={() => {
              autopilot.reset();
              const preflight = runPreflight(buildPreflightInput());
              const stepsToRun = getStepsToExecute(preflight);
              const start = stepsToRun[0] ?? "stage";
              runAutoRunFromStep(start, autopilot, stepsToRun.length > 0 ? stepsToRun : undefined);
            }}
            onCancel={autopilot.cancel}
          />
        </div>
      )}

      {/* Workspace: fills remaining height */}
      <StudioWorkspace />

      {/* Modals */}
      <ImagePreviewModal
        src={imagePreviewSrc}
        candidates={imagePreviewCandidates || undefined}
        onClose={() => setUI({ imagePreviewSrc: null, imagePreviewCandidates: null })}
      />

      <VideoPreviewModal src={videoPreviewSrc} onClose={() => setUI({ videoPreviewSrc: null })} />

      {showGroupModal && projectId && (
        <GroupFormModal
          projectId={projectId}
          onSave={async (data) => {
            const g = await createGroup(data as Parameters<typeof createGroup>[0]);
            if (g) setContext({ groupId: g.id });
          }}
          onClose={() => setShowGroupModal(false)}
        />
      )}

      {showStyleProfileModal && (
        <StyleProfileModal
          defaultProfileId={loadedProfileId}
          onComplete={(profile) =>
            handleStyleProfileComplete(profile, { setShowStyleProfileModal })
          }
          onSkip={() => {
            setShowStyleProfileModal(false);
            showToast("Style profile selection skipped", "success");
          }}
        />
      )}

      {showPreflightModal && (
        <PreflightModal
          isOpen
          preflight={runPreflight(buildPreflightInput())}
          onClose={() => setUI({ showPreflightModal: false })}
          onRun={async (stepsToRun: AutoRunStepId[]) => {
            setUI({ showPreflightModal: false });
            // storyboardId가 없으면 먼저 저장
            if (!useContextStore.getState().storyboardId) {
              const saved = await persistStoryboard();
              if (!saved) {
                showToast("스토리보드 저장에 실패했습니다.", "error");
                return;
              }
            }
            runAutoRunFromStep(stepsToRun[0] || "images", autopilot, stepsToRun);
          }}
        />
      )}
    </div>
  );
}

export default function StudioPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      }
    >
      <StudioContent />
    </Suspense>
  );
}
