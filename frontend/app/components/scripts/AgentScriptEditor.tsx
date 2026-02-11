"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { API_BASE, SCRIPTS_LIST_REFRESH } from "../../constants";
import { useContextStore } from "../../store/useContextStore";
import type { CreativeSession, ShortsSessionCreate } from "../../types/creative";
import ShortsSetupForm from "../lab/ShortsSetupForm";
import ShortsActiveView from "../lab/ShortsActiveView";

export default function AgentScriptEditor() {
  const router = useRouter();
  const [session, setSession] = useState<CreativeSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const handleStoryboardCreated = useCallback(
    (id: number) => {
      useContextStore.getState().setContext({ storyboardId: id });
      window.dispatchEvent(new CustomEvent(SCRIPTS_LIST_REFRESH));
      router.replace(`/scripts?id=${id}`);
    },
    [router]
  );

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
        <p className="text-xs font-semibold text-emerald-800">AI Agent Mode</p>
        <p className="mt-0.5 text-[12px] text-emerald-600">
          AI agents collaborate to create an optimized script through concept debate and pipeline
          execution.
        </p>
      </div>

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
          onStoryboardCreated={handleStoryboardCreated}
        />
      ) : (
        <ShortsSetupForm loading={loading} onSubmit={handleStart} />
      )}
    </div>
  );
}
