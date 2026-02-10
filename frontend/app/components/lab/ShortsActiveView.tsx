"use client";

import axios from "axios";
import { ArrowLeft, RotateCcw, Wrench } from "lucide-react";
import { API_BASE } from "../../constants";
import type {
  CreativeSceneSummary,
  CreativeSession,
  CopyrightResult,
  MusicRecommendation,
} from "../../types/creative";
import StatusBadge from "./StatusBadge";
import ConceptCompareView from "./ConceptCompareView";
import PipelineProgressView from "./PipelineProgressView";
import SessionResultView from "./SessionResultView";
import StepReviewView from "./StepReviewView";
import DebugSlideOver from "./DebugSlideOver";
import { useShortsSession } from "./useShortsSession";
import { useStepReview } from "../../hooks/useStepReview";

type Props = {
  session: CreativeSession;
  onBack: () => void;
  onRefresh: (s: CreativeSession) => void;
};

export default function ShortsActiveView({ session, onBack, onRefresh }: Props) {
  const {
    error,
    showDebug,
    setShowDebug,
    timeline,
    ctx,
    progress,
    candidates,
    handleSelectConcept,
    handleStartPipeline,
    handleSendToStudio,
    handleRetry,
  } = useShortsSession(session, onRefresh);

  const {
    review,
    loading: reviewLoading,
    sending: reviewSending,
    error: reviewError,
    messages: reviewMessages,
    fetchReview,
    handleReviewMessage,
    handleReviewAction,
  } = useStepReview(session.id, session.status);

  const onReviewAction = async (action: "approve" | "revise", feedback?: string) => {
    await handleReviewAction(action, feedback);
    try {
      const res = await axios.get(`${API_BASE}/lab/creative/sessions/${session.id}`);
      onRefresh(res.data);
    } catch {
      /* polling will catch up */
    }
  };

  const renderReviewSection = () => {
    if (reviewLoading && !review) {
      return (
        <div className="flex h-40 items-center justify-center rounded-2xl border border-amber-200 bg-amber-50">
          <div className="text-center">
            <div className="mx-auto mb-2 h-6 w-6 animate-spin rounded-full border-2 border-amber-400 border-t-transparent" />
            <p className="text-xs font-semibold text-amber-700">Loading Review...</p>
          </div>
        </div>
      );
    }
    if (reviewError && !review) {
      return (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5">
          <p className="text-xs font-semibold text-red-700">Review Load Failed</p>
          <p className="mt-1 text-[10px] text-red-500">{reviewError}</p>
          <button
            onClick={fetchReview}
            className="mt-3 flex items-center gap-1.5 rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      );
    }
    if (review) {
      return (
        <StepReviewView
          review={review}
          messages={reviewMessages}
          sending={reviewSending}
          onSendMessage={handleReviewMessage}
          onAction={onReviewAction}
        />
      );
    }
    return null;
  };

  const pipelineState = ctx.pipeline as Record<string, unknown> | undefined;
  const finalOutput = session.final_output as Record<string, unknown> | null;

  return (
    <div className="space-y-4">
      {/* Session header */}
      <div className="rounded-2xl border border-zinc-200 bg-white p-5">
        <div className="mb-3 flex items-center gap-3">
          <button
            onClick={onBack}
            className="flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-50"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </button>
          <StatusBadge status={session.status} />
          <span className="text-[10px] text-zinc-400">#{session.id} • Shorts</span>
          <div className="flex-1" />
          <button
            onClick={() => setShowDebug(!showDebug)}
            className={`flex items-center gap-1 rounded-lg border px-2 py-1 text-[10px] transition ${
              showDebug
                ? "border-indigo-300 bg-indigo-50 text-indigo-600"
                : "border-zinc-200 text-zinc-400 hover:bg-zinc-50"
            }`}
          >
            <Wrench className="h-3 w-3" />
            Debug
          </button>
        </div>
        <p className="text-xs text-zinc-600">{session.objective}</p>
        {ctx.duration ? (
          <p className="mt-1 text-[10px] text-zinc-400">
            {String(ctx.duration)}s • {String(ctx.structure)} • {String(ctx.language)}
          </p>
        ) : null}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {error}
        </div>
      )}

      {/* Status-based view switching */}
      {session.status === "phase1_running" && (
        <div className="flex h-40 items-center justify-center rounded-2xl border border-blue-200 bg-blue-50">
          <div className="text-center">
            <div className="mx-auto mb-2 h-6 w-6 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
            <p className="text-xs font-semibold text-blue-700">Concept Debate Running...</p>
            <p className="text-[10px] text-blue-500">3 architects competing</p>
          </div>
        </div>
      )}

      {session.status === "phase1_done" && (
        <div className="space-y-4">
          <ConceptCompareView
            candidates={candidates}
            evaluationSummary={session.concept_candidates?.evaluation_summary ?? ""}
            selectedIndex={session.selected_concept_index}
            onSelect={handleSelectConcept}
            isAutoSelected={
              session.director_mode === "auto" && session.selected_concept_index !== null
            }
          />
          {session.selected_concept_index !== null && (
            <div className="flex justify-end">
              <button
                onClick={handleStartPipeline}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-emerald-500"
              >
                {session.director_mode === "auto"
                  ? "Auto-starting Pipeline..."
                  : "Confirm & Start Pipeline"}
              </button>
            </div>
          )}
        </div>
      )}

      {session.status === "phase2_running" && (
        <PipelineProgressView progress={progress} topic={session.objective} />
      )}

      {session.status === "step_review" && renderReviewSection()}

      {session.status === "completed" && session.session_type === "shorts" && (
        <SessionResultView
          scenes={(finalOutput?.scenes ?? []) as CreativeSceneSummary[]}
          topic={session.objective}
          musicRecommendation={finalOutput?.music_recommendation as MusicRecommendation | undefined}
          copyrightResult={
            (pipelineState?.state as Record<string, unknown> | undefined)
              ?.copyright_reviewer_result as CopyrightResult | undefined
          }
          onSendToStudio={handleSendToStudio}
        />
      )}

      {session.status === "failed" && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold text-red-700">Pipeline Failed</p>
              <p className="mt-1 text-[10px] text-red-500">
                {(pipelineState?.error as string) ?? "Unknown error"}
              </p>
            </div>
            <button
              onClick={() => handleRetry()}
              className="flex items-center gap-1.5 rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Debug slide-over */}
      {showDebug && timeline && (
        <DebugSlideOver timeline={timeline} onClose={() => setShowDebug(false)} />
      )}
    </div>
  );
}
