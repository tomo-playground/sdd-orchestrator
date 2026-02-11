"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useStudioStore } from "../../store/useStudioStore";
import { useContextStore } from "../../store/useContextStore";
import StudioKanbanView from "../../components/studio/StudioKanbanView";
import StudioTimelineView from "../../components/studio/StudioTimelineView";

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
import { useStudioOnboarding } from "../../hooks/useStudioOnboarding";
import { createGroup } from "../../store/actions/groupActions";
import { SUB_NAV_CLASSES, CONTAINER_CLASSES, cx } from "../../components/ui/variants";
import { runAutoRunFromStep } from "../../store/actions/autopilotActions";
import { saveStoryboard } from "../../store/actions/storyboardActions";
import { handleStyleProfileComplete } from "../../store/actions/styleProfileActions";
import { suggestPromptSplit, copyPromptHelperText } from "../../store/actions/promptHelperActions";
import PreflightModal from "../../components/common/PreflightModal";
import { runPreflight, buildPreflightInput } from "../../utils/preflight";
import type { AutoRunStepId } from "../../utils/preflight";

function StudioContent() {
  const { isLoadingDb, loadedProfileId, storyboardId, needsStyleProfile } =
    useStudioInitialization();
  const { showStyleProfileModal, setShowStyleProfileModal } = useStudioOnboarding({
    isLoadingDb,
    storyboardId,
    needsStyleProfile,
  });

  // Routing: storyboardId determines kanban vs timeline
  const contextStoryboardId = useContextStore((s) => s.storyboardId);
  const resolvedId = storyboardId ? parseInt(storyboardId, 10) : contextStoryboardId;
  const hasStoryboard = !!resolvedId && !isNaN(resolvedId as number);

  // Store selectors
  const setMeta = useStudioStore((s) => s.setMeta);
  const scenes = useStudioStore((s) => s.scenes);
  const storyboardTitle = useStudioStore((s) => s.storyboardTitle);
  const imagePreviewSrc = useStudioStore((s) => s.imagePreviewSrc);
  const imagePreviewCandidates = useStudioStore((s) => s.imagePreviewCandidates);
  const videoPreviewSrc = useStudioStore((s) => s.videoPreviewSrc);
  const showToast = useStudioStore((s) => s.showToast);
  const showPreflightModal = useStudioStore((s) => s.showPreflightModal);
  const groups = useStudioStore((s) => s.groups);
  const projectId = useStudioStore((s) => s.projectId);
  const isRendering = useStudioStore((s) => s.isRendering);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    try {
      await saveStoryboard();
    } finally {
      setIsSaving(false);
    }
  }, []);

  // Prompt Helper state
  const isHelperOpen = useStudioStore((s) => s.isHelperOpen);
  const examplePrompt = useStudioStore((s) => s.examplePrompt);
  const suggestedBase = useStudioStore((s) => s.suggestedBase);
  const suggestedScene = useStudioStore((s) => s.suggestedScene);
  const isSuggesting = useStudioStore((s) => s.isSuggesting);
  const copyStatus = useStudioStore((s) => s.copyStatus);

  // Autopilot
  const autopilot = useAutopilot();

  const isAutoRunningRef = useRef(false);
  isAutoRunningRef.current = autopilot.isAutoRunning;
  useEffect(() => {
    if (!isAutoRunningRef.current) {
      autopilot.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storyboardId]);

  // Warn before refresh/close during render or autopilot
  useEffect(() => {
    if (!isRendering && !autopilot.isAutoRunning) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isRendering, autopilot.isAutoRunning]);

  if (isLoadingDb) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // Kanban view: no storyboard selected
  if (!hasStoryboard) {
    return <StudioKanbanView />;
  }

  // Timeline view: storyboard selected
  return (
    <>
      {/* Sub-header: context bar + global actions */}
      <div className={SUB_NAV_CLASSES}>
        <div className={cx(CONTAINER_CLASSES, "flex items-center justify-between py-2")}>
          <ContextBar title={storyboardTitle || "New Storyboard"} />
          <div className="flex items-center gap-2">
            {scenes.length > 0 && (
              <span className="text-[12px] text-zinc-400">{scenes.length} scenes</span>
            )}
            <StoryboardActionsBar
              onAutoRun={() => setMeta({ showPreflightModal: true })}
              onSave={handleSave}
              isRendering={isRendering}
              isAutoRunning={autopilot.isAutoRunning}
              isSaving={isSaving}
              autoRunStep={autopilot.autoRunState.step}
              showSave={scenes.length > 0}
            />
          </div>
        </div>
      </div>

      {/* No-group banner */}
      {groups.length === 0 && (
        <div className="w-full max-w-5xl px-6 pt-3">
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

      {/* AutoRun Status */}
      {autopilot.autoRunState.status !== "idle" && (
        <div className="w-full max-w-5xl px-6 pt-3">
          <AutoRunStatus
            autoRunState={autopilot.autoRunState}
            autoRunLog={autopilot.autoRunLog}
            storyboardTitle={storyboardTitle || undefined}
            onResume={(step) => runAutoRunFromStep(step, autopilot)}
            onRestart={() => runAutoRunFromStep("images", autopilot)}
          />
        </div>
      )}

      {/* Timeline View */}
      <StudioTimelineView storyboardId={resolvedId as number} />

      {/* Sidebars & Modals */}
      <PromptHelperSidebar
        isOpen={isHelperOpen}
        onClose={() => setMeta({ isHelperOpen: false })}
        examplePrompt={examplePrompt}
        setExamplePrompt={(v) => setMeta({ examplePrompt: v })}
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
        onClose={() => setMeta({ imagePreviewSrc: null, imagePreviewCandidates: null })}
      />

      <VideoPreviewModal src={videoPreviewSrc} onClose={() => setMeta({ videoPreviewSrc: null })} />

      {showGroupModal && projectId && (
        <GroupFormModal
          projectId={projectId}
          onSave={async (data) => {
            const g = await createGroup(data as Parameters<typeof createGroup>[0]);
            if (g) setMeta({ groupId: g.id });
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
          onClose={() => setMeta({ showPreflightModal: false })}
          onRun={(stepsToRun: AutoRunStepId[]) => {
            setMeta({ showPreflightModal: false });
            runAutoRunFromStep(stepsToRun[0] || "images", autopilot, stepsToRun);
          }}
        />
      )}
    </>
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
