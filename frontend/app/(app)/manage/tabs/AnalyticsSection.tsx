"use client";

import type { EditAnalytics } from "../hooks/useSettingsTab";

type Props = {
    analytics: EditAnalytics | null;
    isLoadingAnalytics: boolean;
    analyticsStoryboardFilter: number | null;
    fetchAnalytics: (storyboardId?: number | null) => Promise<void>;
};

export default function AnalyticsSection({
    analytics,
    isLoadingAnalytics,
    analyticsStoryboardFilter,
    fetchAnalytics,
}: Props) {
    return (
        <div className="grid gap-6">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                <span className="text-[12px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                    Performance Analytics
                </span>
                <button
                    type="button"
                    onClick={() => fetchAnalytics(analyticsStoryboardFilter)}
                    disabled={isLoadingAnalytics}
                    className="rounded-full bg-white border border-zinc-200 px-4 py-1.5 text-[12px] font-bold text-zinc-600 shadow-sm hover:bg-zinc-50 transition-colors disabled:opacity-50"
                >
                    {isLoadingAnalytics ? "Loading..." : "Refresh Analytics"}
                </button>
            </div>

            {analytics && (
                <div className="grid gap-6">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
                            <div className="flex items-end justify-between mb-2">
                                <div className="text-3xl font-black text-zinc-900">{analytics.total_edits}</div>
                                <div className="text-xs font-bold text-zinc-400">EDITS</div>
                            </div>
                            <p className="text-[12px] font-medium text-zinc-400 uppercase tracking-widest">Total Auto-Edits</p>
                        </div>

                        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 shadow-sm">
                            <div className="flex items-end justify-between mb-2">
                                <div className="text-3xl font-black text-emerald-600">
                                    +{(analytics.avg_improvement * 100).toFixed(1)}%
                                </div>
                                <div className="text-xs font-bold text-emerald-400">AVG</div>
                            </div>
                            <p className="text-[12px] font-medium text-emerald-500 uppercase tracking-widest">Match Rate Boost</p>
                        </div>

                        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
                            <div className="flex items-end justify-between mb-2">
                                <div className="text-3xl font-black text-amber-600">
                                    ${analytics.total_cost_usd.toFixed(2)}
                                </div>
                                <div className="text-xs font-bold text-amber-400">USD</div>
                            </div>
                            <p className="text-[12px] font-medium text-amber-500 uppercase tracking-widest">Total Investment</p>
                        </div>
                    </div>

                    {/* Improvement Range Distribution */}
                    {analytics.by_improvement_range && Object.keys(analytics.by_improvement_range).length > 0 && (
                        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
                            <h4 className="mb-4 text-[12px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                                Improvement Distribution
                            </h4>
                            <div className="grid gap-3">
                                {Object.entries(analytics.by_improvement_range)
                                    .sort(([a], [b]) => a.localeCompare(b))
                                    .map(([range, count]) => {
                                        const maxCount = Math.max(...Object.values(analytics.by_improvement_range));
                                        const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;

                                        let colorClass = "bg-zinc-400";
                                        if (range.includes("20-30") || range.includes("30+")) {
                                            colorClass = "bg-emerald-500";
                                        } else if (range.includes("10-20")) {
                                            colorClass = "bg-indigo-500";
                                        } else if (range.includes("0-10")) {
                                            colorClass = "bg-amber-500";
                                        }

                                        return (
                                            <div key={range} className="grid grid-cols-[120px_1fr_60px] items-center gap-3">
                                                <span className="text-[12px] font-bold text-zinc-600 uppercase">{range}</span>
                                                <div className="h-6 w-full rounded-full bg-zinc-100 overflow-hidden">
                                                    <div
                                                        className={`h-full ${colorClass} transition-all duration-500`}
                                                        style={{ width: `${percentage}%` }}
                                                    />
                                                </div>
                                                <span className="text-sm font-black text-zinc-700 text-right">{count}</span>
                                            </div>
                                        );
                                    })}
                            </div>
                        </div>
                    )}

                    {/* Recent Edits Table */}
                    {analytics.edits && analytics.edits.length > 0 && (
                        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
                            <h4 className="mb-4 text-[12px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                                Recent Auto-Edits ({analytics.edits.length})
                            </h4>
                            <div className="max-h-[400px] overflow-y-auto custom-scrollbar">
                                <table className="w-full text-xs">
                                    <thead className="sticky top-0 bg-white border-b border-zinc-200">
                                        <tr className="text-[12px] font-bold text-zinc-400 uppercase">
                                            <th className="pb-2 text-left">Storyboard</th>
                                            <th className="pb-2 text-left">Scene</th>
                                            <th className="pb-2 text-right">Before</th>
                                            <th className="pb-2 text-right">After</th>
                                            <th className="pb-2 text-right">Boost</th>
                                            <th className="pb-2 text-right">Cost</th>
                                            <th className="pb-2 text-left">Date</th>
                                        </tr>
                                    </thead>
                                    <tbody className="text-zinc-600">
                                        {analytics.edits.slice(0, 20).map((edit) => {
                                            const improvement = edit.improvement * 100;
                                            let improvementColor = "text-zinc-600";
                                            if (improvement >= 20) {
                                                improvementColor = "text-emerald-600 font-bold";
                                            } else if (improvement >= 10) {
                                                improvementColor = "text-indigo-600 font-semibold";
                                            } else if (improvement >= 5) {
                                                improvementColor = "text-amber-600";
                                            }

                                            return (
                                                <tr key={edit.id} className="border-b border-zinc-100 hover:bg-zinc-50">
                                                    <td className="py-2 font-semibold">#{edit.storyboard_id}</td>
                                                    <td className="py-2">Scene {edit.scene_id}</td>
                                                    <td className="py-2 text-right text-rose-600 font-mono">
                                                        {(edit.original_match_rate * 100).toFixed(0)}%
                                                    </td>
                                                    <td className="py-2 text-right text-emerald-600 font-mono font-bold">
                                                        {(edit.final_match_rate * 100).toFixed(0)}%
                                                    </td>
                                                    <td className={`py-2 text-right font-mono ${improvementColor}`}>
                                                        +{improvement.toFixed(1)}%
                                                    </td>
                                                    <td className="py-2 text-right text-amber-600 font-mono">
                                                        ${edit.cost_usd.toFixed(4)}
                                                    </td>
                                                    <td className="py-2 text-[12px] text-zinc-400">
                                                        {new Date(edit.created_at).toLocaleDateString()}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {analytics.total_edits === 0 && (
                        <div className="flex flex-col items-center justify-center py-12 text-center rounded-2xl border border-zinc-200 bg-zinc-50/50">
                            <p className="text-sm font-bold text-zinc-500">No auto-edits yet</p>
                            <p className="text-[12px] text-zinc-400 mt-1">
                                Enable Auto Edit and start generating scenes to see analytics
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
