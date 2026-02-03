"use client";

import Link from "next/link";
import { useSettingsTab } from "../hooks/useSettingsTab";
import AnalyticsSection from "./AnalyticsSection";
import CacheRefreshSection from "./CacheRefreshSection";
import MediaAssetsSection from "./MediaAssetsSection";

export default function SettingsTab() {
    const {
        storageStats,
        isLoadingStorage,
        cleanupResult,
        isCleaningUp,
        cleanupOptions,
        setCleanupOptions,
        fetchStorageStats,
        handleCleanup,
        autoEditSettings,
        costSummary,
        isLoadingAutoEdit,
        fetchAutoEditSettings,
        analytics,
        isLoadingAnalytics,
        analyticsStoryboardFilter,
        fetchAnalytics,
        mediaStats,
        isLoadingMediaStats,
        fetchMediaStats,
        orphanReport,
        isScanning,
        handleOrphanScan,
        mediaCleanupResult,
        isMediaCleaning,
        handleMediaCleanup,
        isRefreshingCaches,
        cacheRefreshResult,
        handleRefreshCaches,
    } = useSettingsTab();

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
                                        <p className="text-[11px] font-medium text-zinc-400">Ready for maintenance cycle</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Gemini Auto Edit Configuration */}
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

                                <div className="rounded-xl bg-indigo-50 border border-indigo-200 p-4 text-center">
                                    <p className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest mb-1">
                                        Configuration Source
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

            {/* System Caches */}
            <CacheRefreshSection
                isRefreshingCaches={isRefreshingCaches}
                cacheRefreshResult={cacheRefreshResult}
                handleRefreshCaches={handleRefreshCaches}
            />

            {/* Media Assets GC */}
            <MediaAssetsSection
                mediaStats={mediaStats}
                isLoadingMediaStats={isLoadingMediaStats}
                fetchMediaStats={fetchMediaStats}
                orphanReport={orphanReport}
                isScanning={isScanning}
                handleOrphanScan={handleOrphanScan}
                mediaCleanupResult={mediaCleanupResult}
                isMediaCleaning={isMediaCleaning}
                handleMediaCleanup={handleMediaCleanup}
            />

            {/* Performance Analytics */}
            <AnalyticsSection
                analytics={analytics}
                isLoadingAnalytics={isLoadingAnalytics}
                analyticsStoryboardFilter={analyticsStoryboardFilter}
                fetchAnalytics={fetchAnalytics}
            />

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
