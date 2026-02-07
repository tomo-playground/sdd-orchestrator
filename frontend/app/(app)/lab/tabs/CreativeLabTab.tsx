"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import {
  Loader2,
  Play,
  ArrowLeft,
  Send,
  CheckCircle,
  XCircle,
  Clock,
  Settings,
} from "lucide-react";
import { API_BASE } from "../../../constants";
import CreativeRoundView from "../../../components/lab/CreativeRoundView";
import AgentConfigPanel from "../../../components/lab/AgentConfigPanel";
import SessionHistoryTable from "../../../components/lab/SessionHistoryTable";

// ── Types ────────────────────────────────────────────────────

type CreativeSession = {
  id: number;
  task_type: string;
  objective: string;
  evaluation_criteria: Record<string, unknown> | null;
  character_id: number | null;
  context: Record<string, unknown> | null;
  agent_config: Array<Record<string, unknown>> | null;
  final_output: Record<string, unknown> | null;
  max_rounds: number;
  total_token_usage: Record<string, unknown> | null;
  status: string;
  created_at: string | null;
};

type SessionListResponse = {
  items: CreativeSession[];
  total: number;
};

type SendToStudioResponse = {
  storyboard_id: number;
  scenes_created: number;
};

// ── Status badge ─────────────────────────────────────────────

const STATUS_STYLES: Record<string, { bg: string; text: string; icon: typeof CheckCircle }> = {
  completed: { bg: "bg-emerald-50", text: "text-emerald-700", icon: CheckCircle },
  running: { bg: "bg-blue-50", text: "text-blue-700", icon: Loader2 },
  failed: { bg: "bg-red-50", text: "text-red-700", icon: XCircle },
  pending: { bg: "bg-zinc-100", text: "text-zinc-600", icon: Clock },
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  const Icon = style.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${style.bg} ${style.text}`}
    >
      <Icon className={`h-3 w-3 ${status === "running" ? "animate-spin" : ""}`} />
      {status}
    </span>
  );
}

// ── Panel type ───────────────────────────────────────────────

type Panel = "main" | "config";

// ── Main Component ───────────────────────────────────────────

export default function CreativeLabTab() {
  const [sessions, setSessions] = useState<CreativeSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<CreativeSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [debateLoading, setDebateLoading] = useState(false);
  const [sendLoading, setSendLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [panel, setPanel] = useState<Panel>("main");

  // Form state
  const [taskType, setTaskType] = useState("scenario");
  const [objective, setObjective] = useState("");
  const [maxRounds, setMaxRounds] = useState(3);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await axios.get<SessionListResponse>(
        `${API_BASE}/lab/creative/sessions`,
        { params: { limit: 50, offset: 0 } }
      );
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
      const createRes = await axios.post<CreativeSession>(
        `${API_BASE}/lab/creative/sessions`,
        { task_type: taskType, objective: objective.trim(), max_rounds: maxRounds }
      );
      const debateRes = await axios.post<CreativeSession>(
        `${API_BASE}/lab/creative/sessions/${createRes.data.id}/run-debate`
      );
      setSelectedSession(debateRes.data);
      setObjective("");
      await fetchSessions();
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.detail ?? err.message
        : "Failed to run debate";
      setError(String(msg));
    } finally {
      setDebateLoading(false);
    }
  }, [objective, taskType, maxRounds, fetchSessions]);

  const handleSendToStudio = useCallback(async () => {
    if (!selectedSession) return;
    setSendLoading(true);
    setError(null);
    try {
      const res = await axios.post<SendToStudioResponse>(
        `${API_BASE}/lab/creative/sessions/${selectedSession.id}/send-to-studio`,
        {}
      );
      alert(
        `Sent to Studio: storyboard #${res.data.storyboard_id}, ${res.data.scenes_created} scene(s) created.`
      );
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.detail ?? err.message
        : "Failed to send to studio";
      setError(String(msg));
    } finally {
      setSendLoading(false);
    }
  }, [selectedSession]);

  const handleSelectSession = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get<CreativeSession>(
        `${API_BASE}/lab/creative/sessions/${id}`
      );
      setSelectedSession(res.data);
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.detail ?? err.message
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

  // ── Config panel ─────────────────────────────────────────

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

  // ── Main panel ───────────────────────────────────────────

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-800">Creative Lab</h2>
          <p className="mt-0.5 text-xs text-zinc-400">
            Multi-agent creative debate engine
          </p>
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
          sendLoading={sendLoading}
          onBack={handleBack}
          onSendToStudio={handleSendToStudio}
        />
      ) : (
        <>
          <SetupForm
            taskType={taskType}
            objective={objective}
            maxRounds={maxRounds}
            debateLoading={debateLoading}
            onTaskTypeChange={setTaskType}
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

// ── Active Session View ──────────────────────────────────────

function ActiveSessionView({
  session,
  sendLoading,
  onBack,
  onSendToStudio,
}: {
  session: CreativeSession;
  sendLoading: boolean;
  onBack: () => void;
  onSendToStudio: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-zinc-200 bg-white p-5">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="flex items-center gap-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-50"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back to List
            </button>
            <StatusBadge status={session.status} />
            <span className="text-[10px] text-zinc-400">#{session.id}</span>
          </div>
          {session.status === "completed" && (
            <button
              onClick={onSendToStudio}
              disabled={sendLoading}
              className="flex items-center gap-1 rounded-lg bg-zinc-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
            >
              {sendLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
              Send to Studio
            </button>
          )}
        </div>
        <p className="text-xs text-zinc-600">{session.objective}</p>
        {session.final_output && (
          <div className="mt-3 rounded-lg bg-emerald-50 p-3">
            <p className="mb-1 text-[10px] font-semibold tracking-wider text-emerald-600 uppercase">
              Final Output
            </p>
            <pre className="whitespace-pre-wrap text-xs text-emerald-800">
              {JSON.stringify(session.final_output, null, 2)}
            </pre>
          </div>
        )}
      </div>
      <CreativeRoundView sessionId={session.id} />
    </div>
  );
}

// ── Setup Form ───────────────────────────────────────────────

function SetupForm({
  taskType,
  objective,
  maxRounds,
  debateLoading,
  onTaskTypeChange,
  onObjectiveChange,
  onMaxRoundsChange,
  onStartDebate,
}: {
  taskType: string;
  objective: string;
  maxRounds: number;
  debateLoading: boolean;
  onTaskTypeChange: (v: string) => void;
  onObjectiveChange: (v: string) => void;
  onMaxRoundsChange: (v: number) => void;
  onStartDebate: () => void;
}) {
  return (
    <div className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5">
      <p className="text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
        New Creative Session
      </p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Task Type
          </label>
          <select
            value={taskType}
            onChange={(e) => onTaskTypeChange(e.target.value)}
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
          >
            <option value="scenario">Scenario</option>
            <option value="dialogue">Dialogue</option>
            <option value="visual_concept">Visual Concept</option>
            <option value="character_design">Character Design</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Max Rounds
          </label>
          <input
            type="number"
            min={1}
            max={10}
            value={maxRounds}
            onChange={(e) => onMaxRoundsChange(Number(e.target.value))}
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
          />
        </div>
      </div>
      <div>
        <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
          Objective
        </label>
        <textarea
          value={objective}
          onChange={(e) => onObjectiveChange(e.target.value)}
          rows={3}
          placeholder="Describe what you want the agents to create..."
          className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
        />
      </div>
      <div className="flex justify-end">
        <button
          onClick={onStartDebate}
          disabled={debateLoading || !objective.trim()}
          className="flex items-center gap-1.5 rounded-lg bg-zinc-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
        >
          {debateLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          Start Debate
        </button>
      </div>
    </div>
  );
}
