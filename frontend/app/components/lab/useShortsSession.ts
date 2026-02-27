import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { ADMIN_API_BASE } from "../../constants";
import type { CreativeSession, CreativeTimeline, PipelineProgress } from "../../types/creative";

/** Session-level state and side effects for ShortsActiveView. */
export function useShortsSession(
  session: CreativeSession,
  onRefresh: (s: CreativeSession) => void
) {
  const [error, setError] = useState<string | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [timeline, setTimeline] = useState<CreativeTimeline | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const autoStartRef = useRef(false);

  const isPolling = ["phase1_running", "phase2_running"].includes(session.status);

  // --- Side effects ---

  usePolling(session.id, isPolling, onRefresh, pollRef);
  useTimelineFetch(session.id, session.status, showDebug, setTimeline);
  useAutoStartPipeline(session, autoStartRef, () => handleStartPipeline());

  // --- Handlers ---

  const handleSelectConcept = useCallback(
    async (index: number) => {
      setError(null);
      try {
        const res = await axios.post<CreativeSession>(
          `${ADMIN_API_BASE}/lab/creative/sessions/${session.id}/select-concept`,
          { concept_index: index }
        );
        onRefresh(res.data);
      } catch (err) {
        setError(extractErrorMessage(err, "Failed to select concept"));
      }
    },
    [session.id, onRefresh]
  );

  const handleStartPipeline = useCallback(async () => {
    setError(null);
    try {
      await axios.post(`${ADMIN_API_BASE}/lab/creative/sessions/${session.id}/run-pipeline`);
      const res = await axios.get<CreativeSession>(
        `${ADMIN_API_BASE}/lab/creative/sessions/${session.id}`
      );
      onRefresh(res.data);
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to start pipeline"));
    }
  }, [session.id, onRefresh]);

  const handleSendToStudio = useCallback(
    async (groupId: number, title?: string, deepParse?: boolean) => {
      const res = await axios.post(
        `${ADMIN_API_BASE}/lab/creative/sessions/${session.id}/send-to-studio`,
        {
          group_id: groupId,
          title,
          deep_parse: deepParse ?? false,
        }
      );
      return res.data as { storyboard_id?: number };
    },
    [session.id]
  );

  const handleRetry = useCallback(async () => {
    setError(null);
    try {
      await axios.post(`${ADMIN_API_BASE}/lab/creative/sessions/${session.id}/retry`, {
        mode: "resume",
      });
      const sessionRes = await axios.get<CreativeSession>(
        `${ADMIN_API_BASE}/lab/creative/sessions/${session.id}`
      );
      onRefresh(sessionRes.data);
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to retry session"));
    }
  }, [session.id, onRefresh]);

  // --- Derived data ---

  const ctx = (session.context ?? {}) as Record<string, unknown>;
  const progress = ((ctx.pipeline as Record<string, unknown> | undefined)?.progress ??
    null) as PipelineProgress | null;
  const candidates = session.concept_candidates?.candidates ?? [];

  return {
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
  };
}

// ── Internal hooks ──────────────────────────────────────────

function usePolling(
  sessionId: number,
  isPolling: boolean,
  onRefresh: (s: CreativeSession) => void,
  pollRef: React.MutableRefObject<ReturnType<typeof setInterval> | null>
) {
  useEffect(() => {
    if (!isPolling) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }

    const poll = async () => {
      try {
        const res = await axios.get<CreativeSession>(
          `${ADMIN_API_BASE}/lab/creative/sessions/${sessionId}`
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
  }, [sessionId, isPolling, onRefresh, pollRef]);
}

function useTimelineFetch(
  sessionId: number,
  status: string,
  showDebug: boolean,
  setTimeline: (t: CreativeTimeline | null) => void
) {
  useEffect(() => {
    if (!showDebug) return;
    const fetchTimeline = async () => {
      try {
        const res = await axios.get<CreativeTimeline>(
          `${ADMIN_API_BASE}/lab/creative/sessions/${sessionId}/timeline`
        );
        setTimeline(res.data);
      } catch {
        /* ignore */
      }
    };
    fetchTimeline();
  }, [sessionId, status, showDebug, setTimeline]);
}

function useAutoStartPipeline(
  session: CreativeSession,
  autoStartRef: React.MutableRefObject<boolean>,
  startPipeline: () => void
) {
  useEffect(() => {
    if (
      session.status === "phase1_done" &&
      session.director_mode === "auto" &&
      session.selected_concept_index !== null &&
      !autoStartRef.current
    ) {
      autoStartRef.current = true;
      const timer = setTimeout(startPipeline, 0);
      return () => clearTimeout(timer);
    }
    if (session.status !== "phase1_done") {
      autoStartRef.current = false;
    }
  }, [
    session.status,
    session.director_mode,
    session.selected_concept_index,
    autoStartRef,
    startPipeline,
  ]);
}

// ── Helpers ─────────────────────────────────────────────────

function extractErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    return String(err.response?.data?.detail ?? err.message);
  }
  return fallback;
}
