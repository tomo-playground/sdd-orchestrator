"use client";

import type { CacheRefreshResult } from "../hooks/useSettingsTab";

type Props = {
    isRefreshingCaches: boolean;
    cacheRefreshResult: CacheRefreshResult | null;
    handleRefreshCaches: () => Promise<void>;
};

const CACHE_NAMES = ["TagCategory", "TagFilter", "TagAlias", "TagRule", "LoRATrigger"];

export default function CacheRefreshSection({
    isRefreshingCaches,
    cacheRefreshResult,
    handleRefreshCaches,
}: Props) {
    return (
        <div className="grid gap-6">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                <span className="text-[12px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                    System Caches
                </span>
                <button
                    type="button"
                    onClick={handleRefreshCaches}
                    disabled={isRefreshingCaches}
                    className="rounded-full bg-white border border-zinc-200 px-4 py-1.5 text-[12px] font-bold text-zinc-600 shadow-sm hover:bg-zinc-50 transition-colors disabled:opacity-50"
                >
                    {isRefreshingCaches ? "Refreshing..." : "Refresh All Caches"}
                </button>
            </div>

            <div className="flex flex-wrap gap-2">
                {CACHE_NAMES.map((name) => (
                    <span
                        key={name}
                        className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-[12px] font-semibold text-zinc-500"
                    >
                        {name}
                    </span>
                ))}
            </div>

            {cacheRefreshResult && (
                <div
                    className={`rounded-xl border p-3 text-center text-[12px] font-bold uppercase tracking-widest ${
                        cacheRefreshResult.success
                            ? "border-emerald-200 bg-emerald-50 text-emerald-600"
                            : "border-red-200 bg-red-50 text-red-600"
                    }`}
                >
                    {cacheRefreshResult.success
                        ? cacheRefreshResult.message || "All caches refreshed"
                        : cacheRefreshResult.error || "Refresh failed"}
                </div>
            )}
        </div>
    );
}
