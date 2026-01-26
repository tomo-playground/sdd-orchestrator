"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../constants";
import LoadingSpinner from "./LoadingSpinner";

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

export default function QualityDashboard() {
  const [projectName, setProjectName] = useState("my_shorts");
  const [summary, setSummary] = useState<QualitySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadSummary = async () => {
    if (!projectName.trim()) return;

    setLoading(true);
    setError("");

    try {
      const res = await axios.get<QualitySummary>(
        `${API_BASE}/quality/summary/${projectName}`
      );
      setSummary(res.data);
    } catch (err: any) {
      console.error("Failed to load quality summary:", err);
      setError(err.response?.data?.detail || "Failed to load quality data");
    } finally {
      setLoading(false);
    }
  };

  const getScoreBadge = (rate: number) => {
    if (rate >= 0.8) return { emoji: "✅", label: "Excellent", color: "text-emerald-600" };
    if (rate >= 0.7) return { emoji: "⚠️", label: "Good", color: "text-amber-600" };
    return { emoji: "🔴", label: "Poor", color: "text-red-600" };
  };

  const getBarColor = (rate: number) => {
    if (rate >= 0.8) return "bg-emerald-500";
    if (rate >= 0.7) return "bg-amber-500";
    return "bg-red-500";
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
        <input
          type="text"
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          placeholder="Project name"
          className="flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm outline-none focus:border-zinc-400"
        />
        <button
          onClick={loadSummary}
          disabled={loading || !projectName.trim()}
          className="rounded-full bg-zinc-900 px-6 py-2 text-xs font-semibold tracking-wider text-white uppercase transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
        >
          {loading ? (
            <div className="flex items-center gap-2">
              <LoadingSpinner size="sm" color="text-white" />
              <span>Loading...</span>
            </div>
          ) : (
            "Load Quality"
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
              <div className="grid gap-3">
                {summary.scores.map((score) => {
                  const badge = getScoreBadge(score.match_rate);
                  const barColor = getBarColor(score.match_rate);

                  return (
                    <div
                      key={score.scene_id}
                      className="grid grid-cols-[auto_1fr_auto] items-center gap-4 rounded-xl border border-zinc-100 bg-zinc-50 p-3"
                    >
                      <div className="text-sm font-mono text-zinc-500">
                        #{score.scene_id}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <span className={`text-xs font-semibold ${badge.color}`}>
                            {badge.emoji} {badge.label}
                          </span>
                          <span className="text-xs font-mono text-zinc-600">
                            {(score.match_rate * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="relative h-2 overflow-hidden rounded-full bg-zinc-200">
                          <div
                            className={`h-full ${barColor} transition-all`}
                            style={{ width: `${score.match_rate * 100}%` }}
                          />
                        </div>
                        {score.missing_tags.length > 0 && (
                          <div className="mt-2 text-[10px] text-zinc-500">
                            Missing: {score.missing_tags.slice(0, 5).join(", ")}
                            {score.missing_tags.length > 5 && ` (+${score.missing_tags.length - 5} more)`}
                          </div>
                        )}
                      </div>
                      <div className="text-xs text-zinc-400">
                        {score.matched_tags.length}/{score.matched_tags.length + score.missing_tags.length}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
