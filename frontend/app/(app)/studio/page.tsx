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
import ImagePreviewModal from "../../components/ui/ImagePreviewModal";
import VideoPreviewModal from "../../components/ui/VideoPreviewModal";
import AutoRunStatus from "../../components/storyboard/AutoRunStatus";
import StoryboardActionsBar from "../../components/storyboard/StoryboardActionsBar";
import StyleProfileModal from "../../components/setup/StyleProfileModal";
import PromptHelperSidebar from "../../components/prompt/PromptHelperSidebar";
import { ContextBar, GroupFormModal } from "../../components/context";
import { useAutopilot } from "../../hooks/useAutopilot";
import { useStudioInitialization } from "../../hooks/useStudioInitialization";
import { useCharacterAutoLoad } from "../../hooks/useCharacterAutoLoad";
import { useStudioOnboarding } from "../../hooks/useStudioOnboarding";
import { createGroup } from "../../store/actions/groupActions";
import { SUB_NAV_CLASSES } from "../../components/ui/variants";
import { runAutoRunFromStep } from "../../store/actions/autopilotActions";
import { saveStoryboard } from "../../store/actions/storyboardActions";
import { handleStyleProfileComplete } from "../../store/actions/styleProfileActions";
import { suggestPromptSplit, copyPromptHelperText } from "../../store/actions/promptHelperActions";
import PreflightModal from "../../components/common/PreflightModal";
import { runPreflight, buildPreflightInput } from "../../utils/preflight";
import type { AutoRunStepId } from "../../utils/preflight";
import { useKeyboardShortcuts } from "../../hooks/useKeyboardShortcuts";
import { initAutoSave } from "../../store/effects/autoSave";

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

  // Prompt Helper state
  const isHelperOpen = useUIStore((s) => s.isHelperOpen);
  const examplePrompt = useUIStore((s) => s.examplePrompt);
  const suggestedBase = useUIStore((s) => s.suggestedBase);
  const suggestedScene = useUIStore((s) => s.suggestedScene);
  const isSuggesting = useUIStore((s) => s.isSuggesting);
  const copyStatus = useUIStore((s) => s.copyStatus);

  // Autopilot
  const autopilot = useAutopilot();
  const showAutoRun = autopilot.autoRunState.status !== "idle";

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
  useEffect(() => {
    if (!pendingAutoRun) return;
    useUIStore.getState().setPendingAutoRun(false);
    const preflight = runPreflight(buildPreflightInput());
    if (preflight.errors.length > 0) {
      setUI({ showPreflightModal: true });
    } else {
      runAutoRunFromStep("images", autopilot);
    }
  }, [pendingAutoRun, autopilot, setUI]);

  // Dirty state guard
  const isDirty = useStoryboardStore((s) => s.isDirty);

  // Warn before refresh/close during render, autopilot, or unsaved changes
  useEffect(() => {
    if (!isRendering && !autopilot.isAutoRunning && !isDirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isRendering, autopilot.isAutoRunning, isDirty]);

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
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
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
          <ContextBar title={storyboardTitle || "New Storyboard"} />

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
            showSave={scenes.length > 0}
          />
        </div>
      </div>

      {/* No-group banner — inside flex column, before workspace */}
      {groups.length === 0 && (
        <div className="shrink-0 px-8 pt-3">
          <div className="flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-xs text-amber-800">Create a group to start saving storyboards.</p>
            <button
              onClick={() => setShowGroupModal(true)}
              className="shrink-0 rounded-full bg-amber-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-amber-700"
            >
              + Create Group
            </button>
          </div>
        </div>
      )}

      {/* AutoRun Status — inside flex column, before workspace */}
      {showAutoRun && (
        <div className="shrink-0 px-8 pt-3">
          <AutoRunStatus
            autoRunState={autopilot.autoRunState}
            autoRunLog={autopilot.autoRunLog}
            storyboardTitle={storyboardTitle || undefined}
            onResume={(step) => runAutoRunFromStep(step, autopilot)}
            onRestart={() => runAutoRunFromStep("images", autopilot)}
          />
        </div>
      )}

      {/* Workspace: fills remaining height */}
      <StudioWorkspace />

      {/* Sidebars & Modals */}
      <PromptHelperSidebar
        isOpen={isHelperOpen}
        onClose={() => setUI({ isHelperOpen: false })}
        examplePrompt={examplePrompt}
        setExamplePrompt={(v) => setUI({ examplePrompt: v })}
        onSuggestSplit={suggestPromptSplit}
        isSuggesting={isSuggesting}
        suggestedBase={suggestedBase}
        suggestedScene={suggestedScene}
        copyStatus={copyStatus}
        onCopyText={copyPromptHelperText}
      />

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
          onRun={(stepsToRun: AutoRunStepId[]) => {
            setUI({ showPreflightModal: false });
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
