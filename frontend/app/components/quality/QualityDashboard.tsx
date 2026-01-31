"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import LoadingSpinner from "../ui/LoadingSpinner";

type QualityScore = {
  scene_id: number;
  match_rate: number;
  matched_tags: string[];
  missing_tags: string[];
  validated_at: string | null;
};

type QualitySummary = {
  total_scenes: number;
  average_match_rate: number;
  excellent_count: number;
  good_count: number;
  poor_count: number;
  scores: QualityScore[];
};

export default function QualityDashboard({ storyboardId }: { storyboardId?: number | null }) {
  const [summary, setSummary] = useState<QualitySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadSummary = async () => {
    if (!storyboardId) return;

    setLoading(true);
    setError("");

    try {
      const url = `${API_BASE}/quality/summary/${storyboardId}`;

      const res = await axios.get<QualitySummary>(url);
      setSummary(res.data);
    } catch (err: any) {
      console.error("Failed to load quality summary:", err);
      setError(err.response?.data?.detail || err.message || "Failed to load quality data");
    } finally {
      setLoading(false);
    }
  };

  // Reload when storyboard changes
  useEffect(() => {
    if (storyboardId) {
      loadSummary();
    }
  }, [storyboardId]);

  const getScoreBadge = (rate: number) => {
    if (rate >= 0.8) return { emoji: "✨", label: "EXCELLENT", color: "text-emerald-500", bg: "bg-emerald-50" };
    if (rate >= 0.7) return { emoji: "⚡", label: "STABLE", color: "text-amber-500", bg: "bg-amber-50" };
    return { emoji: "🔥", label: "RETRY", color: "text-rose-500", bg: "bg-rose-50" };
  };

  const getBarColor = (rate: number) => {
    if (rate >= 0.8) return "bg-emerald-500";
    if (rate >= 0.7) return "bg-amber-500";
    return "bg-rose-500";
  };

  return (
    <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
      <div>
        <h2 className="text-xl font-semibold text-zinc-900 mb-2">Quality Dashboard</h2>
        <p className="text-sm text-zinc-600">
          Automatic Match Rate tracking for scene validation
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={loadSummary}
          disabled={loading || !storyboardId}
          className="rounded-full bg-zinc-900 px-6 py-2 text-xs font-semibold tracking-wider text-white uppercase transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
        >
          {loading ? (
            <div className="flex items-center gap-2">
              <LoadingSpinner size="sm" color="text-white" />
              <span>Loading...</span>
            </div>
          ) : (
            "Refresh"
          )}
        </button>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {summary && (
        <div className="grid gap-6">
          {/* Summary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="rounded-2xl border border-zinc-200 bg-white p-4">
              <div className="text-3xl font-bold text-zinc-900">
                {(summary.average_match_rate * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider mt-1">
                Avg Match Rate
              </div>
            </div>
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
              <div className="text-3xl font-bold text-emerald-700">
                {summary.excellent_count}
              </div>
              <div className="text-xs text-emerald-600 uppercase tracking-wider mt-1">
                ✅ Excellent (≥80%)
              </div>
            </div>
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <div className="text-3xl font-bold text-amber-700">
                {summary.good_count}
              </div>
              <div className="text-xs text-amber-600 uppercase tracking-wider mt-1">
                ⚠️ Good (70-80%)
              </div>
            </div>
            <div className="rounded-2xl border border-red-200 bg-red-50 p-4">
              <div className="text-3xl font-bold text-red-700">
                {summary.poor_count}
              </div>
              <div className="text-xs text-red-600 uppercase tracking-wider mt-1">
                🔴 Poor (&lt;70%)
              </div>
            </div>
          </div>

          {/* Scene List */}
          {summary.total_scenes === 0 ? (
            <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-8 text-center text-sm text-zinc-500">
              No quality data found for this project.
              <br />
              Generate scenes and validate them first.
            </div>
          ) : (
            <div className="rounded-2xl border border-zinc-200 bg-white p-4">
              <h3 className="text-sm font-semibold text-zinc-700 mb-4">
                Scene Quality Scores ({summary.total_scenes})
              </h3>
              <div className="grid gap-4">
                {summary.scores.map((score, idx) => {
                  const badge = getScoreBadge(score.match_rate);
                  const barColor = getBarColor(score.match_rate);

                  return (
                    <div
                      key={`${score.scene_id}-${idx}`}
                      className="group grid grid-cols-[auto_1fr_auto] items-center gap-6 rounded-2xl border border-zinc-100 bg-white p-4 transition-all duration-300 hover:border-indigo-200 hover:shadow-md"
                    >
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-zinc-50 text-[10px] font-black text-zinc-400 border border-zinc-100 group-hover:bg-indigo-50 group-hover:text-indigo-400 group-hover:border-indigo-100 transition-colors">
                        #{score.scene_id}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-2">
                          <div className={`flex items-center gap-1.5 rounded-full ${badge.bg} px-2 py-0.5 text-[9px] font-black tracking-wider ${badge.color}`}>
                            <span>{badge.emoji}</span>
                            <span>{badge.label}</span>
                          </div>
                          <span className="text-[11px] font-black text-zinc-900">
                            {(score.match_rate * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="relative h-2 w-full overflow-hidden rounded-full bg-zinc-100">
                          <div
                            className={`h-full ${barColor} shadow-sm transition-all duration-500 ease-out`}
                            style={{ width: `${score.match_rate * 100}%` }}
                          />
                        </div>
                        {score.missing_tags.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            <span className="text-[9px] font-bold text-zinc-400 mr-1">MISSING:</span>
                            {score.missing_tags.slice(0, 5).map((tag, i) => (
                              <span key={i} className="text-[9px] font-medium text-rose-400/80 italic">
                                {tag}{i < 4 && i < score.missing_tags.length - 1 ? "," : ""}
                              </span>
                            ))}
                            {score.missing_tags.length > 5 && <span className="text-[9px] text-zinc-300">+{score.missing_tags.length - 5}</span>}
                          </div>
                        )}
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-[10px] font-bold text-zinc-400">{score.matched_tags.length} TAGS</div>
                        <div className="text-[9px] text-zinc-300">MATCHED</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {!summary && !loading && !error && (
        <div className="rounded-2xl border border-dashed border-zinc-200 bg-zinc-50/50 p-8 text-center text-sm text-zinc-500">
          No quality data found for this storyboard.
        </div>
      )}
    </section>
  );
}
