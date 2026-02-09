"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { ArrowLeft, Settings, Trophy } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { API_BASE } from "../../../constants";
import type {
  CreativeSession,
  CreativeTrace,
  SessionListResponse,
  ShortsSessionCreate,
} from "../../../types/creative";
import StatusBadge from "../../../components/lab/StatusBadge";
import SetupForm from "../../../components/lab/SetupForm";
import CreativeRoundView from "../../../components/lab/CreativeRoundView";
import AgentConfigPanel from "../../../components/lab/AgentConfigPanel";
import SessionHistoryTable from "../../../components/lab/SessionHistoryTable";
import ShortsSetupForm from "../../../components/lab/ShortsSetupForm";
import ShortsActiveView from "../../../components/lab/ShortsActiveView";

// -- Types ----------------------------------------------------------------

type Panel = "main" | "config";
type LabMode = "free" | "shorts";

// -- Main Component -------------------------------------------------------

export default function CreativeLabTab() {
  const [sessions, setSessions] = useState<CreativeSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<CreativeSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [debateLoading, setDebateLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [panel, setPanel] = useState<Panel>("main");
  const [labMode, setLabMode] = useState<LabMode>("shorts");

  // V1 form state
  const [objective, setObjective] = useState("");
  const [maxRounds, setMaxRounds] = useState(3);

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

  // -- V1 handlers --------------------------------------------------------

  const handleStartDebate = useCallback(async () => {
    if (!objective.trim()) return;
    setDebateLoading(true);
    setError(null);
    try {
      const createRes = await axios.post<CreativeSession>(`${API_BASE}/lab/creative/sessions`, {
        objective: objective.trim(),
        max_rounds: maxRounds,
      });
      const debateRes = await axios.post<CreativeSession>(
        `${API_BASE}/lab/creative/sessions/${createRes.data.id}/run-debate`
      );
      setSelectedSession(debateRes.data);
      setObjective("");
      await fetchSessions();
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? err.message)
        : "Failed to run debate";
      setError(String(msg));
    } finally {
      setDebateLoading(false);
    }
  }, [objective, maxRounds, fetchSessions]);

  const handleFinalize = useCallback(
    async (trace: CreativeTrace) => {
      if (!selectedSession) return;
      setError(null);
      try {
        const res = await axios.post<CreativeSession>(
          `${API_BASE}/lab/creative/sessions/${selectedSession.id}/finalize`,
          {
            selected_output: {
              content: trace.output_content,
              agent_role: trace.agent_role,
              score: trace.score,
            },
            reason: `Manual selection: ${trace.agent_role}`,
          }
        );
        setSelectedSession(res.data);
      } catch (err) {
        const msg = axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? err.message)
          : "Failed to finalize";
        setError(String(msg));
      }
    },
    [selectedSession]
  );

  // -- V2 handlers --------------------------------------------------------

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
      <div className="flex items-center justify-between rounded-2xl border border-green-100 bg-gradient-to-br from-green-50 to-white p-5">
        <div className="flex-1">
          <h2 className="mb-2 text-base font-bold text-zinc-800">Creative Lab</h2>
          <p className="text-xs text-zinc-500">
            {labMode === "shorts"
              ? "Multi-agent shorts pipeline: Concept Debate → Script → Visual Design → Studio"
              : "Free-form debate: Leader + Writer multi-agent collaboration"}
          </p>
        </div>
        <div className="ml-4 flex items-center gap-2">
          {/* Mode toggle */}
          <div className="flex rounded-lg border border-zinc-200 bg-zinc-50 p-0.5">
            <button
              onClick={() => setLabMode("free")}
              className={`rounded-md px-3 py-1 text-[10px] font-semibold transition ${
                labMode === "free" ? "bg-white text-zinc-800 shadow-sm" : "text-zinc-500"
              }`}
            >
              Free Debate
            </button>
            <button
              onClick={() => setLabMode("shorts")}
              className={`rounded-md px-3 py-1 text-[10px] font-semibold transition ${
                labMode === "shorts" ? "bg-white text-zinc-800 shadow-sm" : "text-zinc-500"
              }`}
            >
              Shorts Pipeline
            </button>
          </div>
          <button
            onClick={() => setPanel("config")}
            className="flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-50"
          >
            <Settings className="h-3.5 w-3.5" /> Presets
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {error}
        </div>
      )}

      {selectedSession ? (
        selectedSession.session_type === "shorts" ? (
          <ShortsActiveView session={selectedSession} onBack={handleBack} onRefresh={setSelectedSession} />
        ) : (
          <V1ActiveSessionView
            session={selectedSession}
            onBack={handleBack}
            onFinalize={handleFinalize}
          />
        )
      ) : (
        <>
          {labMode === "shorts" ? (
            <ShortsSetupForm loading={debateLoading} onSubmit={handleStartShorts} />
          ) : (
            <SetupForm
              objective={objective}
              maxRounds={maxRounds}
              debateLoading={debateLoading}
              onObjectiveChange={setObjective}
              onMaxRoundsChange={setMaxRounds}
              onStartDebate={handleStartDebate}
            />
          )}
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

// -- V1 Active Session View -----------------------------------------------

function V1ActiveSessionView({
  session,
  onBack,
  onFinalize,
}: {
  session: CreativeSession;
  onBack: () => void;
  onFinalize: (trace: CreativeTrace) => void;
}) {
  const finalOutput = session.final_output as Record<string, unknown> | null;

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-zinc-200 bg-white p-5">
        <div className="mb-3 flex items-center gap-3">
          <button
            onClick={onBack}
            className="flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-50"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </button>
          <StatusBadge status={session.status} />
          <span className="text-[10px] text-zinc-400">#{session.id}</span>
        </div>
        <p className="text-xs text-zinc-600">{session.objective}</p>
      </div>

      {finalOutput && (
        <div className="rounded-2xl border-2 border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Trophy className="h-4 w-4 text-emerald-600" />
              <h3 className="text-sm font-semibold text-emerald-900">Final Output</h3>
            </div>
            {finalOutput.agent_role != null && (
              <span className="flex items-center gap-1 rounded-lg bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                {String(finalOutput.agent_role)}
                {finalOutput.score != null && ` • ${Number(finalOutput.score).toFixed(2)}`}
              </span>
            )}
          </div>
          <div className="prose prose-sm prose-emerald max-h-80 max-w-none overflow-y-auto rounded-lg border border-emerald-100 bg-white p-4">
            <ReactMarkdown>
              {String(finalOutput.content ?? JSON.stringify(session.final_output, null, 2))}
            </ReactMarkdown>
          </div>
        </div>
      )}

      <CreativeRoundView sessionId={session.id} session={session} onFinalize={onFinalize} />
    </div>
  );
}

