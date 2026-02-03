"use client";

import { Suspense, useState } from "react";
import { useRouter } from "next/navigation";
import { useStudioStore } from "../store/useStudioStore";
import type { AutoRunStepId } from "../types";
import TabBar from "../components/studio/TabBar";
import PlanTab from "../components/studio/PlanTab";
import ScenesTab from "../components/studio/ScenesTab";
import RenderTab from "../components/studio/RenderTab";
import OutputTab from "../components/studio/OutputTab";
import InsightsTab from "../components/studio/InsightsTab";
import Toast from "../components/ui/Toast";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import ImagePreviewModal from "../components/ui/ImagePreviewModal";
import VideoPreviewModal from "../components/ui/VideoPreviewModal";
import AutoRunStatus from "../components/storyboard/AutoRunStatus";
import StyleProfileModal from "../components/setup/StyleProfileModal";
import PromptHelperSidebar from "../components/prompt/PromptHelperSidebar";
import { ContextBar, GroupFormModal } from "../components/context";
import { useAutopilot } from "../hooks/useAutopilot";
import { useStudioInitialization } from "../hooks/useStudioInitialization";
import { useStudioOnboarding } from "../hooks/useStudioOnboarding";
import { createGroup } from "../store/actions/groupActions";
import CommandPalette from "../components/ui/CommandPalette";
import { runAutoRunFromStep } from "../store/actions/autopilotActions";
import { handleStyleProfileComplete } from "../store/actions/styleProfileActions";
import { suggestPromptSplit, copyPromptHelperText } from "../store/actions/promptHelperActions";

function StudioContent() {
  const router = useRouter();
  const { isLoadingDb, loadedProfileId, storyboardId, needsStyleProfile } =
    useStudioInitialization();
  const {
    showStyleProfileModal,
    setShowStyleProfileModal,
  } = useStudioOnboarding({ isLoadingDb, storyboardId, needsStyleProfile });

  // Store selectors for rendering
  const activeTab = useStudioStore((s) => s.activeTab);
  const setActiveTab = useStudioStore((s) => s.setActiveTab);
  const toast = useStudioStore((s) => s.toast);
  const setMeta = useStudioStore((s) => s.setMeta);
  const scenes = useStudioStore((s) => s.scenes);
  const storyboardTitle = useStudioStore((s) => s.storyboardTitle);
  const imagePreviewSrc = useStudioStore((s) => s.imagePreviewSrc);
  const imagePreviewCandidates = useStudioStore((s) => s.imagePreviewCandidates);
  const videoPreviewSrc = useStudioStore((s) => s.videoPreviewSrc);
  const showToast = useStudioStore((s) => s.showToast);

  // Group empty-state
  const groups = useStudioStore((s) => s.groups);
  const projectId = useStudioStore((s) => s.projectId);
  const [showGroupModal, setShowGroupModal] = useState(false);

  // Prompt Helper state
  const isHelperOpen = useStudioStore((s) => s.isHelperOpen);
  const examplePrompt = useStudioStore((s) => s.examplePrompt);
  const suggestedBase = useStudioStore((s) => s.suggestedBase);
  const suggestedScene = useStudioStore((s) => s.suggestedScene);
  const isSuggesting = useStudioStore((s) => s.isSuggesting);
  const copyStatus = useStudioStore((s) => s.copyStatus);

  // Autopilot state (shared across all tabs)
  const autopilot = useAutopilot();

  if (isLoadingDb) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-50 via-white to-zinc-100 font-[family-name:var(--font-sans)]">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-zinc-100 bg-white/90 backdrop-blur-md transition-all duration-300">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-0.5">
            <button
              data-testid="studio-home-btn"
              onClick={() => router.push("/")}
              className="shrink-0 rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 transition"
              title="Home"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955a1.126 1.126 0 011.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
              </svg>
            </button>
            <svg className="h-3.5 w-3.5 shrink-0 text-zinc-300" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
            </svg>
            <ContextBar title={storyboardTitle || "New Storyboard"} />
          </div>
          <div className="flex items-center gap-2 text-[10px] text-zinc-400">
            {scenes.length > 0 && <span>{scenes.length} scenes</span>}
            {storyboardId && (
              <span className="rounded bg-zinc-100 px-2 py-0.5">
                ID: {storyboardId}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Tab Bar */}
      <TabBar
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* No-group banner */}
      {groups.length === 0 && (
        <div className="mx-auto max-w-5xl px-6 pt-3">
          <div className="flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-xs text-amber-800">
              Create a group to start saving storyboards.
            </p>
            <button
              onClick={() => setShowGroupModal(true)}
              className="shrink-0 rounded-full bg-amber-600 px-3 py-1 text-xs font-semibold text-white hover:bg-amber-700 transition"
            >
              + Create Group
            </button>
          </div>
        </div>
      )}

      {/* Tab Content */}
      <main className="mx-auto max-w-5xl px-6 py-8 pb-32">
        {autopilot.autoRunState.status !== "idle" && (
          <div className="mb-4">
            <AutoRunStatus
              autoRunState={autopilot.autoRunState}
              autoRunLog={autopilot.autoRunLog}
              onResume={() => runAutoRunFromStep(autopilot.autoRunState.step as AutoRunStepId, autopilot)}
              onRestart={() => runAutoRunFromStep("storyboard", autopilot)}
            />
          </div>
        )}

        <div data-testid="tab-content-scenes" style={{ display: activeTab === "scenes" ? "block" : "none" }}>
          <ScenesTab />
        </div>

        {activeTab === "plan" && <div data-testid="tab-content-plan"><PlanTab autopilot={autopilot} /></div>}
        {activeTab === "render" && <div data-testid="tab-content-render"><RenderTab /></div>}
        {activeTab === "output" && <div data-testid="tab-content-output"><OutputTab /></div>}
        {activeTab === "insights" && <div data-testid="tab-content-insights"><InsightsTab /></div>}
      </main>

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

      {toast && <Toast message={toast.message} type={toast.type} />}

      <ImagePreviewModal
        src={imagePreviewSrc}
        candidates={imagePreviewCandidates || undefined}
        onClose={() => setMeta({ imagePreviewSrc: null, imagePreviewCandidates: null })}
      />

      <VideoPreviewModal
        src={videoPreviewSrc}
        onClose={() => setMeta({ videoPreviewSrc: null })}
      />

      {/* Group Create Modal (empty-state) */}
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

      <CommandPalette />

      {/* Style Profile Modal */}
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
