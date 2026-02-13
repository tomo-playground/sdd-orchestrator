"use client";

import { useCallback, useState } from "react";
import axios from "axios";
import { ArrowLeft, Settings } from "lucide-react";
import { API_BASE } from "../../constants";
import type { CreativeSession, ShortsSessionCreate } from "../../types/creative";
import ShortsSetupForm from "../lab/ShortsSetupForm";
import ShortsActiveView from "../lab/ShortsActiveView";
import AgentConfigPanel from "../lab/AgentConfigPanel";

type Props = {
  onStoryboardCreated: (id: number) => void;
};

type Panel = "main" | "config";

export default function AgentScriptEditor({ onStoryboardCreated }: Props) {
  const [session, setSession] = useState<CreativeSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [panel, setPanel] = useState<Panel>("main");

  const handleStart = useCallback(async (data: ShortsSessionCreate) => {
    setLoading(true);
    setError(null);
    try {
      const createRes = await axios.post<CreativeSession>(
        `${API_BASE}/lab/creative/sessions/shorts`,
        data
      );
      await axios.post(`${API_BASE}/lab/creative/sessions/${createRes.data.id}/run-debate`);
      const sessionRes = await axios.get<CreativeSession>(
        `${API_BASE}/lab/creative/sessions/${createRes.data.id}`
      );
      setSession(sessionRes.data);
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? err.message)
        : "Failed to start agent pipeline";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleBack = useCallback(() => {
    setSession(null);
    setError(null);
  }, []);

  if (panel === "config") {
    return (
      <div className="space-y-4">
        <button
          onClick={() => setPanel("main")}
          className="flex items-center gap-1 text-xs text-zinc-500 transition hover:text-zinc-700"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Pipeline
        </button>
        <AgentConfigPanel />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Config toggle */}
      {!session && (
        <div className="flex justify-end">
          <button
            onClick={() => setPanel("config")}
            className="flex items-center gap-1 rounded-lg border border-zinc-200 px-2.5 py-1.5 text-xs text-zinc-500 transition hover:bg-zinc-50 hover:text-zinc-700"
            title="Agent Presets"
          >
            <Settings className="h-3.5 w-3.5" />
            Agent Presets
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {error}
        </div>
      )}

      {session ? (
        <ShortsActiveView
          session={session}
          onBack={handleBack}
          onRefresh={setSession}
          onStoryboardCreated={onStoryboardCreated}
        />
      ) : (
        <ShortsSetupForm loading={loading} onSubmit={handleStart} />
      )}
    </div>
  );
}
