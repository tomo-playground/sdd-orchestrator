"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";

type TagStat = {
  tag: string;
  success_rate: number;
  occurrences: number;
  avg_match_rate: number;
  group?: string;
};

type CategoryTags = {
  [category: string]: TagStat[];
};

type SuggestedCombination = {
  tags: string[];
  categories: string[];
  avg_success_rate: number;
  conflict_free: boolean;
};

type SuccessCombinationsResponse = {
  summary: {
    total_success: number;
    analyzed_tags: number;
    categories_found: number;
  };
  combinations_by_category: CategoryTags;
  suggested_combinations: SuggestedCombination[];
};

export default function AnalyticsDashboard() {
  const [projectName, setProjectName] = useState("");
  const [data, setData] = useState<SuccessCombinationsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const loadAnalytics = async () => {
    if (!projectName.trim()) {
      setError("Please enter a project name");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = await axios.get<SuccessCombinationsResponse>(
        `${API_BASE}/generation-logs/success-combinations`,
        {
          params: {
            project_name: projectName,
            match_rate_threshold: 0.7,
            min_occurrences: 2,
            top_n_per_category: 10,
          },
        }
      );
      setData(response.data);
    } catch (err: any) {
      console.error("Failed to load analytics:", err);
      setError(err.response?.data?.detail || "Failed to load analytics data");
    } finally {
      setIsLoading(false);
    }
  };

  const categoryColors: Record<string, string> = {
    expression: "bg-pink-500",
    pose: "bg-blue-500",
    camera: "bg-purple-500",
    environment: "bg-green-500",
    lighting: "bg-yellow-500",
    mood: "bg-indigo-500",
    clothing: "bg-red-500",
    hair: "bg-orange-500",
  };

  const getCategoryColor = (category: string) => {
    return categoryColors[category] || "bg-gray-500";
  };

  return (
    <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-zinc-900">
            Analytics Dashboard
          </h2>
          <p className="text-xs text-zinc-500">
            Analyze successful tag combinations from generation logs
          </p>
        </div>
      </div>

      {/* Input Section */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          placeholder="Enter project name"
          className="flex-1 min-w-[200px] rounded-full border border-zinc-200 bg-white px-4 py-2 text-[11px] outline-none focus:border-zinc-400"
        />
        <button
          onClick={loadAnalytics}
          disabled={isLoading}
          className="rounded-full bg-zinc-900 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-white uppercase disabled:bg-zinc-400 transition"
        >
          {isLoading ? "Loading..." : "Analyze"}
        </button>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {data && (
        <div className="grid gap-6">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
              <p className="text-[10px] font-semibold tracking-wider uppercase text-emerald-700">
                Success Cases
              </p>
              <p className="text-3xl font-bold text-emerald-900">
                {data.summary.total_success}
              </p>
            </div>
            <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4">
              <p className="text-[10px] font-semibold tracking-wider uppercase text-blue-700">
                Tags Analyzed
              </p>
              <p className="text-3xl font-bold text-blue-900">
                {data.summary.analyzed_tags}
              </p>
            </div>
            <div className="rounded-2xl border border-purple-200 bg-purple-50 p-4">
              <p className="text-[10px] font-semibold tracking-wider uppercase text-purple-700">
                Categories
              </p>
              <p className="text-3xl font-bold text-purple-900">
                {data.summary.categories_found}
              </p>
            </div>
          </div>

          {/* Suggested Combinations */}
          {data.suggested_combinations.length > 0 && (
            <div className="rounded-2xl border border-zinc-200 bg-white p-6">
              <h3 className="text-sm font-semibold text-zinc-900 mb-4">
                Suggested Combinations
              </h3>
              <div className="grid gap-4">
                {data.suggested_combinations.map((combo, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-zinc-100 bg-zinc-50 p-4"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-zinc-700">
                        Combination #{idx + 1}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-zinc-600">
                          Success Rate: {(combo.avg_success_rate * 100).toFixed(1)}%
                        </span>
                        {combo.conflict_free ? (
                          <span className="rounded-full bg-emerald-100 px-2 py-1 text-[9px] font-semibold text-emerald-700">
                            ✓ Conflict-Free
                          </span>
                        ) : (
                          <span className="rounded-full bg-amber-100 px-2 py-1 text-[9px] font-semibold text-amber-700">
                            ⚠ Has Conflicts
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {combo.tags.map((tag, tagIdx) => (
                        <span
                          key={tagIdx}
                          className={`rounded-full ${getCategoryColor(combo.categories[tagIdx])} bg-opacity-10 border border-current px-3 py-1 text-[10px] font-medium`}
                          style={{
                            color: `var(--${combo.categories[tagIdx]}-color, #666)`,
                          }}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Tags by Category */}
          <div className="grid gap-4">
            <h3 className="text-sm font-semibold text-zinc-900">
              Top Tags by Category
            </h3>
            {Object.entries(data.combinations_by_category).map(([category, tags]) => (
              <div
                key={category}
                className="rounded-2xl border border-zinc-200 bg-white p-4"
              >
                <h4 className="text-xs font-semibold tracking-wider uppercase text-zinc-700 mb-3">
                  {category}
                </h4>
                <div className="grid gap-2">
                  {tags.slice(0, 5).map((tag, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] font-bold text-zinc-400">
                          #{idx + 1}
                        </span>
                        <span className="text-xs font-medium text-zinc-900">
                          {tag.tag}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-[10px]">
                        <span className="text-emerald-700">
                          {(tag.success_rate * 100).toFixed(0)}% success
                        </span>
                        <span className="text-zinc-500">
                          {tag.occurrences}x used
                        </span>
                        <span className="text-blue-700">
                          {(tag.avg_match_rate * 100).toFixed(0)}% match
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!data && !isLoading && !error && (
        <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-8 text-center">
          <p className="text-sm text-zinc-500">
            Enter a project name and click Analyze to view insights
          </p>
        </div>
      )}
    </section>
  );
}
