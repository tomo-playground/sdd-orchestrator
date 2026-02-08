"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { ArrowLeft, Settings, Trophy } from "lucide-react";
import { API_BASE } from "../../../constants";
import type { CreativeSession, CreativeTrace, SessionListResponse } from "../../../types/creative";
import StatusBadge from "../../../components/lab/StatusBadge";
import SetupForm from "../../../components/lab/SetupForm";
import CreativeRoundView from "../../../components/lab/CreativeRoundView";
import AgentConfigPanel from "../../../components/lab/AgentConfigPanel";
import SessionHistoryTable from "../../../components/lab/SessionHistoryTable";

// -- Panel type -----------------------------------------------------------

type Panel = "main" | "config";

// -- Main Component -------------------------------------------------------

export default function CreativeLabTab() {
  const [sessions, setSessions] = useState<CreativeSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<CreativeSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [debateLoading, setDebateLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [panel, setPanel] = useState<Panel>("main");

  // Form state
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

  const handleStartDebate = useCallback(async () => {
    if (!objective.trim()) return;
    setDebateLoading(true);
    setError(null);
    try {
      const createRes = await axios.post<CreativeSession>(`${API_BASE}/lab/creative/sessions`, {
        task_type: "scenario",
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
  }, []);

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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-800">Creative Lab</h2>
          <p className="mt-0.5 text-xs text-zinc-400">Multi-agent creative debate engine</p>
        </div>
        <button
          onClick={() => setPanel("config")}
          className="flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-50"
        >
          <Settings className="h-3.5 w-3.5" /> Agent Presets
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {error}
        </div>
      )}

      {selectedSession ? (
        <ActiveSessionView
          session={selectedSession}
          onBack={handleBack}
          onFinalize={handleFinalize}
        />
      ) : (
        <>
          <SetupForm
            objective={objective}
            maxRounds={maxRounds}
            debateLoading={debateLoading}
            onObjectiveChange={setObjective}
            onMaxRoundsChange={setMaxRounds}
            onStartDebate={handleStartDebate}
          />
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

// -- Active Session View --------------------------------------------------

function ActiveSessionView({
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
            <ArrowLeft className="h-3.5 w-3.5" /> Back to List
          </button>
          <StatusBadge status={session.status} />
          <span className="text-[10px] text-zinc-400">#{session.id}</span>
        </div>
        <p className="text-xs text-zinc-600">{session.objective}</p>
        {finalOutput && (
          <div className="mt-3 rounded-lg bg-emerald-50 p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-[10px] font-semibold tracking-wider text-emerald-600 uppercase">
                Final Output
              </p>
              {finalOutput.agent_role != null && (
                <span className="flex items-center gap-1 rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                  <Trophy className="h-3 w-3" />
                  {String(finalOutput.agent_role)}
                  {finalOutput.score != null && ` (${Number(finalOutput.score).toFixed(2)})`}
                </span>
              )}
            </div>
            <pre className="max-h-60 overflow-y-auto text-xs leading-relaxed whitespace-pre-wrap text-emerald-800">
              {String(finalOutput.content ?? JSON.stringify(session.final_output, null, 2))}
            </pre>
          </div>
        )}
      </div>
      <CreativeRoundView sessionId={session.id} session={session} onFinalize={onFinalize} />
    </div>
  );
}
