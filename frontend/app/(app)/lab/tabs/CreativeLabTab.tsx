"use client";

import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { ArrowLeft, Settings, Trophy } from "lucide-react";
import ReactMarkdown from "react-markdown";
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
      {/* ── Purpose Section ── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between rounded-2xl border border-green-100 bg-gradient-to-br from-green-50 to-white p-5">
          <div className="flex-1">
            <h2 className="mb-2 text-base font-bold text-zinc-800">Creative Lab</h2>
            <p className="text-xs leading-relaxed text-zinc-600">
              <strong className="text-zinc-700">목표:</strong> Leader + Writer 멀티 에이전트가
              협업하여 고품질 스토리보드를 생성합니다.
            </p>
            <p className="mt-1.5 text-xs leading-relaxed text-zinc-500">
              Leader 에이전트가 전체 방향을 제시하고, Writer 에이전트가 초안을 작성합니다.
              여러 라운드의 피드백을 통해 스토리보드를 점진적으로 개선합니다.
            </p>

            {/* Collapsible Details */}
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-semibold text-green-700 hover:text-green-800">
                📖 자세히 보기
              </summary>
              <div className="mt-3 space-y-3 rounded-lg border border-green-100 bg-white p-3 text-xs">
                <div>
                  <strong className="text-zinc-700">💡 사용 시나리오:</strong>
                  <ul className="ml-4 mt-1 list-disc space-y-0.5 text-zinc-600">
                    <li>다양한 스토리보드 아이디어를 빠르게 탐색</li>
                    <li>에이전트 페르소나 및 설정 최적화</li>
                    <li>Leader/Writer 협업 품질 개선 실험</li>
                  </ul>
                </div>
                <div>
                  <strong className="text-zinc-700">✅ 성공 기준:</strong>
                  <span className="ml-1 text-zinc-600">
                    <strong className="text-emerald-600">3라운드 내</strong> 만족스러운 스토리보드 생성
                  </span>
                </div>
                <div>
                  <strong className="text-zinc-700">📊 주요 메트릭:</strong>
                  <span className="ml-1 text-zinc-600">
                    Round Count, Agent Agreement, Quality Score
                  </span>
                </div>
                <div>
                  <strong className="text-zinc-700">🔄 워크플로우:</strong>
                  <span className="ml-1 text-zinc-600">
                    Creative Lab → 검증 → Studio로 복사하여 이미지 생성
                  </span>
                </div>
                <div>
                  <strong className="text-zinc-700">⚡ Quick Tips:</strong>
                  <ul className="ml-4 mt-1 list-disc space-y-0.5 text-zinc-600">
                    <li>Max Rounds 3-5 추천 (너무 많으면 과최적화)</li>
                    <li>Objective는 명확하고 구체적으로</li>
                  </ul>
                </div>
              </div>
            </details>
          </div>

          <button
            onClick={() => setPanel("config")}
            className="ml-4 flex items-center gap-1 self-start rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-600 hover:bg-zinc-50"
          >
            <Settings className="h-3.5 w-3.5" /> Agent Presets
          </button>
        </div>
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
      {/* Session Info Card */}
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
      </div>

      {/* Final Output Card - Independent & Emphasized */}
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

      {/* Rounds History */}
      <CreativeRoundView sessionId={session.id} session={session} onFinalize={onFinalize} />
    </div>
  );
}
