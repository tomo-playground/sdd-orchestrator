"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import axios from "axios";
import { API_BASE } from "../../constants";
import LoadingSpinner from "../../components/ui/LoadingSpinner";

type StorageStats = {
    total_size_mb: number;
    total_count: number;
    directories: Record<string, { count: number; size_mb: number }>;
};

type CleanupResult = {
    deleted_count: number;
    freed_mb: number;
    dry_run: boolean;
    details: Record<string, { deleted: number; freed_mb: number; files?: string[] }>;
};

type AutoEditSettings = {
    enabled: boolean;
    threshold: number;
    max_cost_per_storyboard: number;
    max_retries_per_scene: number;
};

type CostSummary = {
    today: number;
    this_week: number;
    this_month: number;
    total: number;
    edit_count_today: number;
    edit_count_month: number;
};

type EditAnalytics = {
    total_edits: number;
    total_cost_usd: number;
    avg_improvement: number;
    edits: Array<{
        id: number;
        storyboard_id: number;
        scene_id: number;
        original_match_rate: number;
        final_match_rate: number;
        improvement: number;
        cost_usd: number;
        created_at: string;
    }>;
    by_improvement_range: Record<string, number>;
};

export default function SettingsTab() {
    // Storage state
    const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
    const [isLoadingStorage, setIsLoadingStorage] = useState(false);
    const [cleanupResult, setCleanupResult] = useState<CleanupResult | null>(null);
    const [isCleaningUp, setIsCleaningUp] = useState(false);
    const [cleanupOptions, setCleanupOptions] = useState({
        cleanup_videos: true,
        video_max_age_days: 7,
        cleanup_cache: true,
        cleanup_test_folders: true,
        cleanup_candidates: false,
    });

    // Gemini Auto Edit state
    const [autoEditSettings, setAutoEditSettings] = useState<AutoEditSettings | null>(null);
    const [costSummary, setCostSummary] = useState<CostSummary | null>(null);
    const [isLoadingAutoEdit, setIsLoadingAutoEdit] = useState(false);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [isSavingAutoEdit, setIsSavingAutoEdit] = useState(false);

    // Gemini Analytics state
    const [analytics, setAnalytics] = useState<EditAnalytics | null>(null);
    const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(false);
    const [analyticsStoryboardFilter, setAnalyticsStoryboardFilter] = useState<number | null>(null);

    const fetchStorageStats = async () => {
        setIsLoadingStorage(true);
        try {
            const res = await axios.get(`${API_BASE}/storage/stats`);
            setStorageStats(res.data);
        } catch {
            setStorageStats(null);
        } finally {
            setIsLoadingStorage(false);
        }
    };

    const handleCleanup = async (dryRun: boolean) => {
        setIsCleaningUp(true);
        setCleanupResult(null);
        try {
            const res = await axios.post(`${API_BASE}/storage/cleanup`, {
                ...cleanupOptions,
                dry_run: dryRun,
            });
            setCleanupResult(res.data);
            if (!dryRun) {
                await fetchStorageStats();
            }
        } catch {
            alert("Cleanup failed.");
        } finally {
            setIsCleaningUp(false);
        }
    };

    const fetchAutoEditSettings = async () => {
        setIsLoadingAutoEdit(true);
        try {
            const [settingsRes, costRes] = await Promise.all([
                axios.get(`${API_BASE}/settings/auto-edit`),
                axios.get(`${API_BASE}/settings/auto-edit/cost-summary`),
            ]);
            setAutoEditSettings(settingsRes.data);
            setCostSummary(costRes.data);
        } catch {
            setAutoEditSettings(null);
            setCostSummary(null);
        } finally {
            setIsLoadingAutoEdit(false);
        }
    };

    // Note: Save function removed from UI in original code? 
    // Ah, looking at original code, saveAutoEditSettings was defined but the UI controls are disabled/read-only 
    // with a notice that settings are in .env. 
    // I will keep logic consistent with the original file (Read Only UI).

    const fetchAnalytics = async (storyboardId?: number | null) => {
        setIsLoadingAnalytics(true);
        try {
            const params = storyboardId ? { storyboard_id: storyboardId } : {};
            const res = await axios.get(`${API_BASE}/analytics/gemini-edits`, { params });
            setAnalytics(res.data);
        } catch {
            setAnalytics(null);
        } finally {
            setIsLoadingAnalytics(false);
        }
    };

    useEffect(() => {
        void fetchStorageStats();
        void fetchAutoEditSettings();
        void fetchAnalytics(analyticsStoryboardFilter);
    }, [analyticsStoryboardFilter]);

    return (
        <section className="grid gap-8 rounded-2xl border border-zinc-200/60 bg-white p-8 text-xs text-zinc-600 shadow-sm">
            {/* Storage Section */}
            <div className="grid gap-6">
                <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                    <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                        Workspace Storage
                    </span>
                    <button
                        type="button"
                        onClick={fetchStorageStats}
                        disabled={isLoadingStorage}
                        className="rounded-full bg-white border border-zinc-200 px-4 py-1.5 text-[10px] font-bold text-zinc-600 shadow-sm hover:bg-zinc-50 transition-colors disabled:opacity-50"
                    >
                        {isLoadingStorage ? "Syncing..." : "Sync Stats"}
                    </button>
                </div>

                {storageStats && (
                    <div className="grid gap-6">
                        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
                            <div className="mb-6 flex items-end justify-between">
                                <div>
                                    <div className="text-3xl font-black text-zinc-900">
                                        {storageStats.total_size_mb.toFixed(1)} <span className="text-sm font-bold text-zinc-400">MB</span>
                                    </div>
                                    <p className="mt-1 text-[11px] font-medium text-zinc-400 uppercase tracking-widest">Aggregate Usage</p>
                                </div>
                                <div className="text-right">
                                    <div className="text-sm font-bold text-indigo-600">{storageStats.total_count}</div>
                                    <p className="text-[10px] font-medium text-zinc-400">TOTAL OBJECTS</p>
                                </div>
                            </div>

                            {/* Visual Progress Bar */}
                            <div className="h-3 w-full flex rounded-full bg-zinc-100 overflow-hidden mb-8">
                                {Object.entries(storageStats.directories).map(([name, stats], idx) => {
                                    const percent = (stats.size_mb / (storageStats.total_size_mb || 1)) * 100;
                                    const colors = ["bg-indigo-500", "bg-emerald-500", "bg-amber-500", "bg-rose-500", "bg-sky-500"];
                                    return (
                                        <div
                                            key={name}
                                            style={{ width: `${percent}%` }}
                                            className={`${colors[idx % colors.length]} h-full border-r border-white/20 last:border-0`}
                                            title={`${name}: ${stats.size_mb.toFixed(1)} MB`}
                                        />
                                    );
                                })}
                            </div>

                            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                                {Object.entries(storageStats.directories).map(([name, stats], idx) => {
                                    const colors = ["bg-indigo-500", "bg-emerald-500", "bg-amber-500", "bg-rose-500", "bg-sky-500"];
                                    return (
                                        <div key={name} className="flex items-center gap-3 p-3 rounded-2xl border border-zinc-50 bg-zinc-50/50">
                                            <div className={`h-2 w-2 rounded-full ${colors[idx % colors.length]}`} />
                                            <div className="flex-1 min-w-0">
                                                <p className="text-[10px] font-bold text-zinc-700 uppercase tracking-tighter truncate">{name}</p>
                                                <p className="text-[11px] font-medium text-zinc-400">
                                                    {stats.size_mb.toFixed(1)} MB · {stats.count} items
                                                </p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Cleanup Matrix */}
                        <div className="grid md:grid-cols-2 gap-6">
                            <div className="rounded-2xl border border-zinc-200 bg-white p-6">
                                <h4 className="mb-4 text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">Retention Policies</h4>
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between p-3 rounded-2xl bg-zinc-50/50 border border-zinc-50">
                                        <label className="flex items-center gap-3 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={cleanupOptions.cleanup_videos}
                                                onChange={(e) => setCleanupOptions(p => ({ ...p, cleanup_videos: e.target.checked }))}
                                                className="h-4 w-4 rounded-lg border-zinc-300 text-indigo-600 focus:ring-indigo-500"
                                            />
                                            <div>
                                                <p className="text-xs font-bold text-zinc-700">Video Retention</p>
                                                <p className="text-[10px] text-zinc-400">Purge old video files from exports</p>
                                            </div>
                                        </label>
                                        <div className="flex items-center gap-2 bg-white border border-zinc-200 rounded-xl px-2 py-1">
                                            <input
                                                type="number"
                                                value={cleanupOptions.video_max_age_days}
                                                onChange={(e) => setCleanupOptions(p => ({ ...p, video_max_age_days: Math.max(1, parseInt(e.target.value) || 1) }))}
                                                className="w-8 text-center text-[10px] font-bold text-zinc-700 outline-none"
                                            />
                                            <span className="text-[9px] font-bold text-zinc-400">DAYS</span>
                                        </div>
                                    </div>

                                    <label className="flex items-center justify-between p-3 rounded-2xl bg-zinc-50/50 border border-zinc-50 cursor-pointer">
                                        <div className="flex items-center gap-3">
                                            <input
                                                type="checkbox"
                                                checked={cleanupOptions.cleanup_cache}
                                                onChange={(e) => setCleanupOptions(p => ({ ...p, cleanup_cache: e.target.checked }))}
                                                className="h-4 w-4 rounded-lg border-zinc-300 text-indigo-600"
                                            />
                                            <div>
                                                <p className="text-xs font-bold text-zinc-700">Cache Expiration</p>
                                                <p className="text-[10px] text-zinc-400">Wipe transient data and temporary assets</p>
                                            </div>
                                        </div>
                                    </label>

                                    <label className="flex items-center justify-between p-3 rounded-2xl bg-zinc-50/50 border border-zinc-50 cursor-pointer">
                                        <div className="flex items-center gap-3">
                                            <input
                                                type="checkbox"
                                                checked={cleanupOptions.cleanup_test_folders}
                                                onChange={(e) => setCleanupOptions(p => ({ ...p, cleanup_test_folders: e.target.checked }))}
                                                className="h-4 w-4 rounded-lg border-zinc-300 text-indigo-600"
                                            />
                                            <div>
                                                <p className="text-xs font-bold text-zinc-700">Test Artifacts</p>
                                                <p className="text-[10px] text-zinc-400">Clean up experiment and test directories</p>
                                            </div>
                                        </div>
                                    </label>
                                </div>

                                <div className="mt-6 flex gap-3">
                                    <button
                                        onClick={() => handleCleanup(true)}
                                        disabled={isCleaningUp}
                                        className="flex-1 rounded-2xl border border-zinc-200 px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-zinc-500 hover:bg-zinc-50 transition-all"
                                    >
                                        Dry Run
                                    </button>
                                    <button
                                        onClick={() => handleCleanup(false)}
                                        disabled={isCleaningUp}
                                        className="flex-1 rounded-2xl bg-zinc-900 px-4 py-3 text-[10px] font-bold uppercase tracking-widest text-white shadow-lg shadow-zinc-200 hover:bg-rose-600 transition-all disabled:bg-zinc-300"
                                    >
                                        {isCleaningUp ? "Cleaning..." : "Execute Purge"}
                                    </button>
                                </div>
                            </div>

                            {/* Cleanup Result Box */}
                            <div className="rounded-2xl border border-zinc-200 bg-zinc-50/50 p-6">
                                <h4 className="mb-4 text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">Operation Result</h4>
                                {cleanupResult ? (
                                    <div className="space-y-4">
                                        <div className="rounded-2xl bg-white p-4 border border-zinc-100 shadow-sm">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-[10px] font-bold text-zinc-400 uppercase">Space Freed</span>
                                                <span className="text-lg font-black text-emerald-600">{cleanupResult.freed_mb.toFixed(1)} MB</span>
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <span className="text-[10px] font-bold text-zinc-400 uppercase">Objects Removed</span>
                                                <span className="text-lg font-black text-indigo-600">{cleanupResult.deleted_count}</span>
                                            </div>
                                            {cleanupResult.dry_run && (
                                                <div className="mt-3 rounded-lg bg-amber-50 p-2 text-center text-[9px] font-bold text-amber-600 uppercase tracking-tighter">
                                                    Simulated Results (Dry Run)
                                                </div>
                                            )}
                                        </div>
                                        <div className="max-h-[160px] overflow-y-auto pr-2 custom-scrollbar">
                                            {Object.entries(cleanupResult.details).map(([dir, info]) => (
                                                <div key={dir} className="flex items-center justify-between py-1.5 border-b border-zinc-100 last:border-0">
                                                    <span className="text-[10px] font-bold text-zinc-500 uppercase">{dir}</span>
                                                    <span className="text-[10px] font-medium text-zinc-400">-{info.freed_mb.toFixed(1)} MB</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex h-full flex-col items-center justify-center py-12 text-center">
                                        <div className="mb-3 text-2xl opacity-20">🍃</div>
                                        <p className="text-[11px] font-medium text-zinc-400">Ready for maintenance cycle</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Gemini Auto Edit Configuration (Phase 6-4.22) */}
            <div className="grid gap-6">
                <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                    <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                        Gemini Auto Edit
                    </span>
                    <button
                        type="button"
                        onClick={fetchAutoEditSettings}
                        disabled={isLoadingAutoEdit}
                        className="rounded-full bg-white border border-zinc-200 px-4 py-1.5 text-[10px] font-bold text-zinc-600 shadow-sm hover:bg-zinc-50 transition-colors disabled:opacity-50"
                    >
                        {isLoadingAutoEdit ? "Loading..." : "Refresh"}
                    </button>
                </div>

                {autoEditSettings && costSummary && (
                    <div className="grid gap-6">
                        {/* Cost Summary Cards */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
                                <div className="text-2xl font-black text-zinc-900">
                                    ${costSummary.today.toFixed(2)}
                                </div>
                                <p className="mt-1 text-[10px] font-medium text-zinc-400 uppercase tracking-widest">Today</p>
                                <p className="text-[9px] text-zinc-400">{costSummary.edit_count_today} edits</p>
                            </div>
                            <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
                                <div className="text-2xl font-black text-zinc-900">
                                    ${costSummary.this_week.toFixed(2)}
                                </div>
                                <p className="mt-1 text-[10px] font-medium text-zinc-400 uppercase tracking-widest">This Week</p>
                            </div>
                            <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
                                <div className="text-2xl font-black text-zinc-900">
                                    ${costSummary.this_month.toFixed(2)}
                                </div>
                                <p className="mt-1 text-[10px] font-medium text-zinc-400 uppercase tracking-widest">This Month</p>
                                <p className="text-[9px] text-zinc-400">{costSummary.edit_count_month} edits</p>
                            </div>
                            <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4 shadow-sm">
                                <div className="text-2xl font-black text-indigo-600">
                                    ${costSummary.total.toFixed(2)}
                                </div>
                                <p className="mt-1 text-[10px] font-medium text-indigo-500 uppercase tracking-widest">Total</p>
                            </div>
                        </div>

                        {/* Settings Controls */}
                        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
                            <div className="grid gap-6">
                                {/* Master Switch - Read Only */}
                                <div className="flex items-center justify-between p-4 rounded-2xl bg-zinc-50/50 border border-zinc-50">
                                    <div>
                                        <p className="text-sm font-bold text-zinc-700">Auto Edit Enabled</p>
                                        <p className="text-[10px] text-zinc-400 mt-1">
                                            Automatically fix images with low Match Rate
                                        </p>
                                    </div>
                                    <label className="relative inline-flex items-center cursor-not-allowed opacity-75">
                                        <input
                                            type="checkbox"
                                            checked={autoEditSettings.enabled}
                                            disabled
                                            className="sr-only peer"
                                        />
                                        <div className="w-11 h-6 bg-zinc-200 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                                    </label>
                                </div>

                                {/* Threshold Slider - Read Only */}
                                <div className="grid gap-3 opacity-75">
                                    <div className="flex items-center justify-between">
                                        <label className="text-xs font-bold text-zinc-700">Match Rate Threshold</label>
                                        <span className="text-sm font-black text-indigo-600">
                                            {(autoEditSettings.threshold * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                    <input
                                        type="range"
                                        min="0.5"
                                        max="0.9"
                                        step="0.05"
                                        value={autoEditSettings.threshold}
                                        disabled
                                        className="w-full h-2 bg-zinc-200 rounded-lg appearance-none cursor-not-allowed accent-indigo-600"
                                    />
                                    <p className="text-[10px] text-zinc-400">
                                        Trigger auto-edit when Match Rate &lt; {(autoEditSettings.threshold * 100).toFixed(0)}%
                                    </p>
                                </div>

                                {/* Max Cost Input - Read Only */}
                                <div className="grid gap-3 opacity-75">
                                    <label className="text-xs font-bold text-zinc-700">Max Cost per Storyboard</label>
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-bold text-zinc-400">$</span>
                                        <input
                                            type="number"
                                            min="0.1"
                                            max="10"
                                            step="0.1"
                                            value={autoEditSettings.max_cost_per_storyboard}
                                            disabled
                                            className="flex-1 rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-2 text-sm font-bold text-zinc-700 cursor-not-allowed"
                                        />
                                    </div>
                                    <p className="text-[10px] text-zinc-400">
                                        Stop auto-editing when storyboard cost exceeds this limit
                                    </p>
                                </div>

                                {/* Max Retries Input - Read Only */}
                                <div className="grid gap-3 opacity-75">
                                    <label className="text-xs font-bold text-zinc-700">Max Retries per Scene</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="5"
                                        step="1"
                                        value={autoEditSettings.max_retries_per_scene}
                                        disabled
                                        className="rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-2 text-sm font-bold text-zinc-700 cursor-not-allowed"
                                    />
                                    <p className="text-[10px] text-zinc-400">
                                        Maximum edit attempts per scene before giving up
                                    </p>
                                </div>

                                {/* .env Configuration Notice */}
                                <div className="rounded-xl bg-indigo-50 border border-indigo-200 p-4 text-center">
                                    <p className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest mb-1">
                                        📄 Configuration Source
                                    </p>
                                    <p className="text-[11px] text-indigo-700">
                                        These settings are managed in <code className="bg-indigo-100 px-1 py-0.5 rounded font-mono">.env</code> file
                                    </p>
                                    <p className="text-[10px] text-indigo-500 mt-2">
                                        Edit <code className="bg-indigo-100 px-1 py-0.5 rounded font-mono">backend/.env</code> to change configuration
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Gemini Analytics Dashboard (Phase 6-4.22) */}
            <div className="grid gap-6">
                <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                    <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                        Performance Analytics
                    </span>
                    <button
                        type="button"
                        onClick={() => fetchAnalytics(analyticsStoryboardFilter)}
                        disabled={isLoadingAnalytics}
                        className="rounded-full bg-white border border-zinc-200 px-4 py-1.5 text-[10px] font-bold text-zinc-600 shadow-sm hover:bg-zinc-50 transition-colors disabled:opacity-50"
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
                                <p className="text-[10px] font-medium text-zinc-400 uppercase tracking-widest">Total Auto-Edits</p>
                            </div>

                            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 shadow-sm">
                                <div className="flex items-end justify-between mb-2">
                                    <div className="text-3xl font-black text-emerald-600">
                                        +{(analytics.avg_improvement * 100).toFixed(1)}%
                                    </div>
                                    <div className="text-xs font-bold text-emerald-400">AVG</div>
                                </div>
                                <p className="text-[10px] font-medium text-emerald-500 uppercase tracking-widest">Match Rate Boost</p>
                            </div>

                            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
                                <div className="flex items-end justify-between mb-2">
                                    <div className="text-3xl font-black text-amber-600">
                                        ${analytics.total_cost_usd.toFixed(2)}
                                    </div>
                                    <div className="text-xs font-bold text-amber-400">USD</div>
                                </div>
                                <p className="text-[10px] font-medium text-amber-500 uppercase tracking-widest">Total Investment</p>
                            </div>
                        </div>

                        {/* Improvement Range Distribution */}
                        {analytics.by_improvement_range && Object.keys(analytics.by_improvement_range).length > 0 && (
                            <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
                                <h4 className="mb-4 text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                                    Improvement Distribution
                                </h4>
                                <div className="grid gap-3">
                                    {Object.entries(analytics.by_improvement_range)
                                        .sort(([a], [b]) => a.localeCompare(b))
                                        .map(([range, count]) => {
                                            const maxCount = Math.max(...Object.values(analytics.by_improvement_range));
                                            const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;

                                            // Color coding based on improvement range
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
                                                    <span className="text-[10px] font-bold text-zinc-600 uppercase">{range}</span>
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
                                <h4 className="mb-4 text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                                    Recent Auto-Edits ({analytics.edits.length})
                                </h4>
                                <div className="max-h-[400px] overflow-y-auto custom-scrollbar">
                                    <table className="w-full text-xs">
                                        <thead className="sticky top-0 bg-white border-b border-zinc-200">
                                            <tr className="text-[10px] font-bold text-zinc-400 uppercase">
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
                                                        <td className="py-2 text-[10px] text-zinc-400">
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
                                <div className="mb-3 text-4xl opacity-20">📊</div>
                                <p className="text-sm font-bold text-zinc-500">No auto-edits yet</p>
                                <p className="text-[10px] text-zinc-400 mt-1">
                                    Enable Auto Edit and start generating scenes to see analytics
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Render Settings Link */}
            <div className="grid gap-3 pt-4 border-t border-zinc-100">
                <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                    Studio Configuration
                </span>
                <div className="flex flex-wrap items-center gap-4">
                    <p className="text-[11px] text-zinc-500 italic max-w-sm">
                        Core rendering parameters and global stylization settings are managed within the main studio interface.
                    </p>
                    <Link
                        href="/"
                        className="rounded-full border border-indigo-200 bg-indigo-50/30 px-6 py-2.5 text-[10px] font-bold tracking-[0.1em] text-indigo-600 uppercase transition hover:bg-indigo-100"
                    >
                        Return to Studio
                    </Link>
                </div>
            </div>
        </section>
    );
}
