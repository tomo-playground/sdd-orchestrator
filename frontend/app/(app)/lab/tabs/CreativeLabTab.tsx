"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { ArrowLeft, Settings } from "lucide-react";
import { API_BASE } from "../../../constants";
import type {
  CreativeSession,
  SessionListResponse,
  ShortsSessionCreate,
} from "../../../types/creative";
import AgentConfigPanel from "../../../components/lab/AgentConfigPanel";
import SessionHistoryTable from "../../../components/lab/SessionHistoryTable";
import ShortsSetupForm from "../../../components/lab/ShortsSetupForm";
import ShortsActiveView from "../../../components/lab/ShortsActiveView";

// -- Types ----------------------------------------------------------------

type Panel = "main" | "config";

// -- Main Component -------------------------------------------------------

export default function CreativeLabTab() {
  const [sessions, setSessions] = useState<CreativeSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<CreativeSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [debateLoading, setDebateLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [panel, setPanel] = useState<Panel>("main");

  const fetchSessions = useCallback(async () => {
    try {
      const res = await axios.get<SessionListResponse>(`${API_BASE}/lab/creative/sessions`, {
        params: { limit: 50, offset: 0 },
      });
      setSessions(res.data.items);
    } catch {
      /* silently fail on list fetch */
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleStartShorts = useCallback(
    async (data: ShortsSessionCreate) => {
      setDebateLoading(true);
      setError(null);
      try {
        const createRes = await axios.post<CreativeSession>(
          `${API_BASE}/lab/creative/sessions/shorts`,
          data
        );
        // Start debate (background task)
        await axios.post(`${API_BASE}/lab/creative/sessions/${createRes.data.id}/run-debate`);
        // Set session — polling will handle status updates
        const sessionRes = await axios.get<CreativeSession>(
          `${API_BASE}/lab/creative/sessions/${createRes.data.id}`
        );
        setSelectedSession(sessionRes.data);
        await fetchSessions();
      } catch (err) {
        const msg = axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? err.message)
          : "Failed to start shorts pipeline";
        setError(String(msg));
      } finally {
        setDebateLoading(false);
      }
    },
    [fetchSessions]
  );

  // -- Common handlers ----------------------------------------------------

  const handleSelectSession = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get<CreativeSession>(`${API_BASE}/lab/creative/sessions/${id}`);
      setSelectedSession(res.data);
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? err.message)
        : "Failed to load session";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleBack = useCallback(() => {
    setSelectedSession(null);
    setError(null);
    fetchSessions();
  }, [fetchSessions]);

  // -- Config panel -------------------------------------------------------

  if (panel === "config") {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setPanel("main")}
          className="flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Creative Lab
        </button>
        <AgentConfigPanel />
      </div>
    );
  }

  // -- Main panel ---------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-green-100 bg-gradient-to-br from-green-50 to-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="mb-2 text-base font-bold text-zinc-800">Creative Lab</h2>
          <button
            onClick={() => setPanel("config")}
            className="ml-4 flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-50"
          >
            <Settings className="h-3.5 w-3.5" /> Presets
          </button>
        </div>
        <p className="text-xs leading-relaxed text-zinc-600">
          <strong className="text-zinc-700">목표:</strong> AI 에이전트 파이프라인으로 쇼츠 영상을
          자동 생성합니다.
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-zinc-500">
          Concept Debate → Script → Visual Design → Sound → Copyright 5단계를 순차 실행하고, 각
          단계마다 QC 검증으로 품질을 보장합니다.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {error}
        </div>
      )}

      {selectedSession ? (
        <ShortsActiveView
          session={selectedSession}
          onBack={handleBack}
          onRefresh={setSelectedSession}
        />
      ) : (
        <>
          <ShortsSetupForm loading={debateLoading} onSubmit={handleStartShorts} />
          <SessionHistoryTable
            sessions={sessions}
            loading={loading}
            onSelect={handleSelectSession}
          />
        </>
      )}
    </div>
  );
}
