"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import { SIDE_PANEL_LAYOUT, SIDE_PANEL_CLASSES } from "../ui/variants";

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

export default function AnalyticsDashboard({ storyboardId }: { storyboardId?: number | null }) {
  const [data, setData] = useState<SuccessCombinationsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const loadAnalytics = async () => {
    if (!storyboardId) return;

    setIsLoading(true);
    setError("");

    try {
      const params: Record<string, unknown> = {
        match_rate_threshold: 0.7,
        min_occurrences: 2,
        top_n_per_category: 10,
      };

      if (storyboardId) {
        params.storyboard_id = storyboardId;
      }

      const response = await axios.get<SuccessCombinationsResponse>(
        `${API_BASE}/activity-logs/success-combinations`,
        { params }
      );
      setData(response.data);
    } catch (err: unknown) {
      console.error("Failed to load analytics:", err);
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(
        axiosErr.response?.data?.detail || axiosErr.message || "Failed to load analytics data"
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Reload when storyboard changes
  useEffect(() => {
    if (storyboardId) {
      loadAnalytics();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storyboardId]);

  const categoryColors: Record<string, string> = {
    expression: "bg-pink-500",
    pose: "bg-blue-500",
    camera: "bg-purple-500",
    environment: "bg-emerald-500",
    lighting: "bg-yellow-500",
    mood: "bg-indigo-500",
    clothing: "bg-red-500",
    hair: "bg-orange-500",
  };

  const getCategoryColor = (category: string) => {
    return categoryColors[category] || "bg-zinc-500";
  };

  return (
    <div className={SIDE_PANEL_LAYOUT}>
      {/* Left */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-zinc-900">Analytics</h2>
            <p className="text-xs text-zinc-500">Tag combinations from generation logs.</p>
          </div>
          <button
            onClick={loadAnalytics}
            disabled={isLoading || !storyboardId}
            className="rounded-full bg-zinc-900 px-4 py-1.5 text-[12px] font-semibold tracking-wider text-white uppercase transition disabled:bg-zinc-400"
          >
            {isLoading ? "Loading..." : "Refresh"}
          </button>
        </div>

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {data && data.summary.total_success === 0 && (
          <div className="rounded-2xl border border-dashed border-zinc-200 bg-zinc-50 p-6 text-center text-sm text-zinc-500">
            No successful generations found for analysis.
          </div>
        )}

        {data && data.summary.total_success > 0 && (
          <div className="grid gap-6">
            {data.suggested_combinations.length > 0 && (
              <div className="rounded-2xl border border-zinc-200 bg-white p-6">
                <h3 className="mb-4 text-sm font-semibold text-zinc-900">Suggested Combinations</h3>
                <div className="grid gap-4">
                  {data.suggested_combinations.map((combo, idx) => (
                    <div key={idx} className="rounded-xl border border-zinc-100 bg-zinc-50 p-4">
                      <div className="mb-2 flex items-center justify-between">
                        <span className="text-xs font-semibold text-zinc-700">
                          Combination #{idx + 1}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-zinc-600">
                            {(combo.avg_success_rate * 100).toFixed(1)}%
                          </span>
                          <span
                            className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${combo.conflict_free ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}
                          >
                            {combo.conflict_free ? "✓" : "⚠"}
                          </span>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {combo.tags.map((tag, tagIdx) => (
                          <span
                            key={tagIdx}
                            className={`rounded-full ${getCategoryColor(combo.categories[tagIdx])} bg-opacity-10 border border-current px-3 py-1 text-[12px] font-medium`}
                            style={{ color: `var(--${combo.categories[tagIdx]}-color, #666)` }}
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

            <div className="grid gap-4">
              <h3 className="text-sm font-semibold text-zinc-900">Top Tags by Category</h3>
              {Object.entries(data.combinations_by_category).map(([category, tags]) => (
                <div key={category} className="rounded-2xl border border-zinc-200 bg-white p-4">
                  <h4 className="mb-3 text-xs font-semibold tracking-wider text-zinc-700 uppercase">
                    {category}
                  </h4>
                  <div className="grid gap-2">
                    {tags.slice(0, 5).map((tag, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-[12px] font-bold text-zinc-400">#{idx + 1}</span>
                          <span className="text-xs font-medium text-zinc-900">{tag.tag}</span>
                        </div>
                        <div className="flex items-center gap-4 text-[12px]">
                          <span className="text-emerald-700">
                            {(tag.success_rate * 100).toFixed(0)}%
                          </span>
                          <span className="text-zinc-500">{tag.occurrences}x</span>
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
            <p className="text-sm text-zinc-500">Select a storyboard to view insights</p>
          </div>
        )}
      </div>

      {/* Right: Summary Stats (sticky) */}
      <div className={SIDE_PANEL_CLASSES}>
        {data && data.summary.total_success > 0 ? (
          <div className="grid gap-2">
            <div className="rounded-lg bg-emerald-50 px-3 py-2.5">
              <p className="text-[12px] font-semibold tracking-wider text-emerald-700 uppercase">
                Success
              </p>
              <p className="text-xl font-bold text-emerald-900">{data.summary.total_success}</p>
            </div>
            <div className="rounded-lg bg-blue-50 px-3 py-2.5">
              <p className="text-[12px] font-semibold tracking-wider text-blue-700 uppercase">
                Tags
              </p>
              <p className="text-xl font-bold text-blue-900">{data.summary.analyzed_tags}</p>
            </div>
            <div className="rounded-lg bg-purple-50 px-3 py-2.5">
              <p className="text-[12px] font-semibold tracking-wider text-purple-700 uppercase">
                Categories
              </p>
              <p className="text-xl font-bold text-purple-900">{data.summary.categories_found}</p>
            </div>
          </div>
        ) : (
          <p className="text-center text-[12px] text-zinc-400">No data</p>
        )}
      </div>
    </div>
  );
}
