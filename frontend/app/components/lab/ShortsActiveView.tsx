"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { ArrowLeft, RotateCcw, Wrench } from "lucide-react";
import { API_BASE } from "../../constants";
import type {
  CreativeSession,
  CreativeTimeline,
  CopyrightResult,
  MusicRecommendation,
  PipelineProgress,
} from "../../types/creative";
import StatusBadge from "./StatusBadge";
import ConceptCompareView from "./ConceptCompareView";
import PipelineProgressView from "./PipelineProgressView";
import SessionResultView from "./SessionResultView";
import DebugSlideOver from "./DebugSlideOver";

type Props = {
  session: CreativeSession;
  onBack: () => void;
  onRefresh: (s: CreativeSession) => void;
};

export default function ShortsActiveView({ session, onBack, onRefresh }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [timeline, setTimeline] = useState<CreativeTimeline | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isPolling = ["phase1_running", "phase2_running"].includes(session.status);

  // Poll for status updates
  useEffect(() => {
    if (!isPolling) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }

    const poll = async () => {
      try {
        const res = await axios.get<CreativeSession>(
          `${API_BASE}/lab/creative/sessions/${session.id}`,
        );
        onRefresh(res.data);
      } catch {
        /* ignore poll errors */
      }
    };

    pollRef.current = setInterval(poll, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [session.id, isPolling, onRefresh]);

  // Fetch timeline for debug panel
  useEffect(() => {
    if (!showDebug) return;
    const fetchTimeline = async () => {
      try {
        const res = await axios.get<CreativeTimeline>(
          `${API_BASE}/lab/creative/sessions/${session.id}/timeline`,
        );
        setTimeline(res.data);
      } catch {
        /* ignore */
      }
    };
    fetchTimeline();
  }, [session.id, session.status, showDebug]);

  const handleSelectConcept = useCallback(
    async (index: number) => {
      setError(null);
      try {
        const res = await axios.post<CreativeSession>(
          `${API_BASE}/lab/creative/sessions/${session.id}/select-concept`,
          { concept_index: index },
        );
        onRefresh(res.data);
      } catch (err) {
        const msg = axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? err.message)
          : "Failed to select concept";
        setError(String(msg));
      }
    },
    [session.id, onRefresh],
  );

  const handleStartPipeline = useCallback(async () => {
    setError(null);
    try {
      await axios.post(`${API_BASE}/lab/creative/sessions/${session.id}/run-pipeline`);
      const res = await axios.get<CreativeSession>(
        `${API_BASE}/lab/creative/sessions/${session.id}`,
      );
      onRefresh(res.data);
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? err.message)
        : "Failed to start pipeline";
      setError(String(msg));
    }
  }, [session.id, onRefresh]);

  const handleSendToStudio = useCallback(
    async (groupId: number, title?: string, deepParse?: boolean) => {
      await axios.post(`${API_BASE}/lab/creative/sessions/${session.id}/send-to-studio`, {
        group_id: groupId,
        title,
        deep_parse: deepParse ?? false,
      });
    },
    [session.id],
  );

  const handleRetry = useCallback(async () => {
    setError(null);
    try {
      // Default to "resume" mode for now, could offer "restart" option later
      const res = await axios.post(`${API_BASE}/lab/creative/sessions/${session.id}/retry`, {
        mode: "resume",
      });
      // Immediately refresh with response to update status to running
      if (res.data && res.data.status) {
        // Optimistic update or wait for poll? 
        // Force refresh parent
      }
      // Re-fetch session to get updated status
      const sessionRes = await axios.get<CreativeSession>(
        `${API_BASE}/lab/creative/sessions/${session.id}`,
      );
      onRefresh(sessionRes.data);
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? err.message)
        : "Failed to retry session";
      setError(String(msg));
    }
  }, [session.id, onRefresh]);

  const autoStartRef = useRef(false);

  // Auto-pilot: auto-start pipeline when director auto-selected a concept
  useEffect(() => {
    if (
      session.status === "phase1_done" &&
      session.director_mode === "auto" &&
      session.selected_concept_index !== null &&
      !autoStartRef.current
    ) {
      autoStartRef.current = true;
      // Defer to next tick to avoid cascading setState within effect
      const timer = setTimeout(() => handleStartPipeline(), 0);
      return () => clearTimeout(timer);
    }
    if (session.status !== "phase1_done") {
      autoStartRef.current = false;
    }
  }, [session.status, session.director_mode, session.selected_concept_index, handleStartPipeline]);

  const ctx = (session.context ?? {}) as Record<string, unknown>;
  const progress = ((ctx.pipeline as Record<string, unknown> | undefined)?.progress ??
    null) as PipelineProgress | null;
  const candidates = session.concept_candidates?.candidates ?? [];

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
            className={`flex items-center gap-1 rounded-lg border px-2 py-1 text-[10px] transition ${showDebug
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

      {session.status === "completed" && session.session_type === "shorts" && (
        <SessionResultView
          scenes={
            ((session.final_output as Record<string, unknown> | null)?.scenes ?? []) as Array<{
              order: number;
              script: string;
              speaker: string;
              duration: number;
              camera?: string;
              environment?: string;
              image_prompt?: string;
            }>
          }
          topic={session.objective}
          musicRecommendation={
            (session.final_output as Record<string, unknown> | null)
              ?.music_recommendation as MusicRecommendation | undefined
          }
          copyrightResult={
            (
              (ctx.pipeline as Record<string, unknown> | undefined)?.state as
              | Record<string, unknown>
              | undefined
            )?.copyright_reviewer_result as CopyrightResult | undefined
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
                {((ctx.pipeline as Record<string, unknown> | undefined)?.error as string) ??
                  "Unknown error"}
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
