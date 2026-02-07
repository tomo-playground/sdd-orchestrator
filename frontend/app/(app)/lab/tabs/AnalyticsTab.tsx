"use client";

import { useState, useCallback, useEffect } from "react";
import axios from "axios";
import { RefreshCw, Loader2, ArrowUpRight } from "lucide-react";
import { API_BASE } from "../../../constants";
import QualityDashboard from "../../../components/quality/QualityDashboard";

// ── Types ──────────────────────────────────────────────────────

type TagEffectivenessItem = {
  tag_name: string;
  tag_id: number;
  use_count: number;
  match_count: number;
  effectiveness: number;
};

type TagEffectivenessReport = {
  items: TagEffectivenessItem[];
  total_experiments: number;
  avg_match_rate: number | null;
};

// ── Component ──────────────────────────────────────────────────

export default function AnalyticsTab() {
  const [report, setReport] = useState<TagEffectivenessReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await axios.get<TagEffectivenessReport>(
        `${API_BASE}/lab/analytics/tag-effectiveness`
      );
      setReport(res.data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(axiosErr.response?.data?.detail || axiosErr.message || "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const handleSync = useCallback(async () => {
    setSyncing(true);
    try {
      await axios.post(`${API_BASE}/lab/analytics/sync-effectiveness`);
      await loadReport();
    } catch {
      /* sync errors are non-critical */
    } finally {
      setSyncing(false);
    }
  }, [loadReport]);

  const effectivenessColor = (ratio: number) => {
    if (ratio >= 0.8) return "text-emerald-600";
    if (ratio >= 0.5) return "text-amber-600";
    return "text-rose-600";
  };

  return (
    <div className="space-y-6">
      {/* Quality Dashboard (reused) */}
      <QualityDashboard />

      {/* Tag Effectiveness Section */}
      <div className="rounded-2xl border border-zinc-200 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-zinc-800">Tag Effectiveness</h3>
            {report && (
              <p className="mt-0.5 text-[10px] text-zinc-400">
                {report.total_experiments} experiments
                {report.avg_match_rate != null &&
                  ` / ${(report.avg_match_rate * 100).toFixed(0)}% avg`}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-1.5 rounded-lg border border-zinc-200 px-3 py-1.5 text-[10px] font-semibold text-zinc-600 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {syncing ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <ArrowUpRight className="h-3 w-3" />
              )}
              Sync to Studio
            </button>
            <button
              onClick={loadReport}
              disabled={loading}
              className="flex items-center gap-1.5 rounded-lg border border-zinc-200 px-3 py-1.5 text-[10px] font-semibold text-zinc-600 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="h-3 w-3" />
              )}
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <p className="mb-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-600">{error}</p>
        )}

        {!report && !loading && !error && (
          <p className="py-6 text-center text-xs text-zinc-400">No effectiveness data available.</p>
        )}

        {report && report.items.length === 0 && (
          <p className="py-6 text-center text-xs text-zinc-400">
            Run experiments in Tag Lab to populate effectiveness data.
          </p>
        )}

        {report && report.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-100 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
                  <th className="pr-4 pb-2">Tag</th>
                  <th className="pr-4 pb-2">Uses</th>
                  <th className="pr-4 pb-2">Matches</th>
                  <th className="pb-2">Effectiveness</th>
                </tr>
              </thead>
              <tbody>
                {report.items.map((item, idx) => (
                  <tr
                    key={`${item.tag_id}-${idx}`}
                    className="border-b border-zinc-50 text-zinc-600"
                  >
                    <td className="py-2 pr-4 font-medium">{item.tag_name}</td>
                    <td className="py-2 pr-4 font-mono text-zinc-400">{item.use_count}</td>
                    <td className="py-2 pr-4 font-mono text-zinc-400">{item.match_count}</td>
                    <td className={`py-2 font-bold ${effectivenessColor(item.effectiveness)}`}>
                      {(item.effectiveness * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
