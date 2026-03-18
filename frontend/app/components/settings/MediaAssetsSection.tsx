"use client";

import type { MediaStats, OrphanReport, MediaCleanupResult } from "../../hooks/useSettingsTab";
import { ERROR_BG, ERROR_TEXT } from "../ui/variants";

type Props = {
  mediaStats: MediaStats | null;
  isLoadingMediaStats: boolean;
  fetchMediaStats: () => Promise<void>;
  orphanReport: OrphanReport | null;
  isScanning: boolean;
  handleOrphanScan: () => Promise<void>;
  mediaCleanupResult: MediaCleanupResult | null;
  isMediaCleaning: boolean;
  handleMediaCleanup: (dryRun: boolean) => Promise<void>;
};

export default function MediaAssetsSection({
  mediaStats,
  isLoadingMediaStats,
  fetchMediaStats,
  orphanReport,
  isScanning,
  handleOrphanScan,
  mediaCleanupResult,
  isMediaCleaning,
  handleMediaCleanup,
}: Props) {
  return (
    <div className="grid gap-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
        <span className="text-[12px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
          Media Assets
        </span>
        <button
          type="button"
          onClick={fetchMediaStats}
          disabled={isLoadingMediaStats}
          className="rounded-full border border-zinc-200 bg-white px-4 py-1.5 text-[12px] font-bold text-zinc-600 shadow-sm transition-colors hover:bg-zinc-50 disabled:opacity-50"
        >
          {isLoadingMediaStats ? "Syncing..." : "Sync Stats"}
        </button>
      </div>

      {/* Stats Cards */}
      {mediaStats && (
        <div className="grid gap-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Total Assets" value={mediaStats.total_assets} />
            <StatCard label="Temp Assets" value={mediaStats.temp_assets} color="amber" />
            <StatCard label="No Owner" value={mediaStats.null_owner_assets} color="rose" />
            <StatCard label="Orphans" value={mediaStats.orphan_count} color="red" />
          </div>

          {/* Owner Type Breakdown */}
          {Object.keys(mediaStats.by_owner_type).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(mediaStats.by_owner_type).map(([type, count]) => (
                <span
                  key={type}
                  className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-[12px] font-semibold text-zinc-500"
                >
                  {type}: {count}
                </span>
              ))}
            </div>
          )}

          {/* Scan + Cleanup 2-column */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Left: Orphan Scan */}
            <div className="rounded-2xl border border-zinc-200 bg-white p-6">
              <h4 className="mb-4 text-[12px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                Orphan Detection
              </h4>
              <button
                type="button"
                onClick={handleOrphanScan}
                disabled={isScanning}
                className="w-full rounded-2xl border border-zinc-200 px-4 py-3 text-[12px] font-bold tracking-widest text-zinc-500 uppercase transition-all hover:bg-zinc-50 disabled:opacity-50"
              >
                {isScanning ? "Scanning..." : "Scan Orphans"}
              </button>

              {orphanReport && (
                <div className="mt-4 space-y-3">
                  <OrphanCategory label="Null Owner" items={orphanReport.null_owner} />
                  <OrphanCategory label="Broken FK" items={orphanReport.broken_fk} />
                  <OrphanCategory label="Expired Temp" items={orphanReport.expired_temp} />
                  <div className="rounded-lg bg-zinc-100 p-2 text-center text-[12px] font-bold text-zinc-600">
                    Total: {orphanReport.total} orphan(s)
                  </div>
                </div>
              )}
            </div>

            {/* Right: Cleanup */}
            <div className="rounded-2xl border border-zinc-200 bg-zinc-50/50 p-6">
              <h4 className="mb-4 text-[12px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                Cleanup
              </h4>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => handleMediaCleanup(true)}
                  disabled={isMediaCleaning}
                  className="flex-1 rounded-2xl border border-zinc-200 px-4 py-3 text-[12px] font-bold tracking-widest text-zinc-500 uppercase transition-all hover:bg-zinc-50 disabled:opacity-50"
                >
                  Dry Run
                </button>
                <button
                  type="button"
                  onClick={() => handleMediaCleanup(false)}
                  disabled={isMediaCleaning}
                  className="flex-1 rounded-2xl bg-zinc-900 px-4 py-3 text-[12px] font-bold tracking-widest text-white uppercase shadow-lg shadow-zinc-200 transition-all hover:bg-rose-600 disabled:bg-zinc-300"
                >
                  {isMediaCleaning ? "Cleaning..." : "Execute Purge"}
                </button>
              </div>

              {mediaCleanupResult && (
                <div className="mt-4 space-y-3">
                  <div className="rounded-2xl border border-zinc-100 bg-white p-4 shadow-sm">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-[12px] font-bold text-zinc-400 uppercase">
                        Total Deleted
                      </span>
                      <span className="text-lg font-black text-emerald-600">
                        {mediaCleanupResult.total_deleted}
                      </span>
                    </div>
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-[12px] font-bold text-zinc-400 uppercase">Orphans</span>
                      <span className="text-sm font-bold text-zinc-700">
                        {mediaCleanupResult.orphans.deleted}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[12px] font-bold text-zinc-400 uppercase">
                        Expired Temp
                      </span>
                      <span className="text-sm font-bold text-zinc-700">
                        {mediaCleanupResult.expired_temp.deleted}
                      </span>
                    </div>
                    {mediaCleanupResult.orphans.is_dry_run && (
                      <div className="mt-3 rounded-lg bg-amber-50 p-2 text-center text-[11px] font-bold tracking-tighter text-amber-600 uppercase">
                        Simulated Results (Dry Run)
                      </div>
                    )}
                  </div>

                  {/* Storage errors */}
                  {[
                    ...mediaCleanupResult.orphans.storage_errors,
                    ...mediaCleanupResult.expired_temp.storage_errors,
                  ].length > 0 && (
                    <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-[12px] text-red-600">
                      <p className="mb-1 font-bold">Storage Errors:</p>
                      {[
                        ...mediaCleanupResult.orphans.storage_errors,
                        ...mediaCleanupResult.expired_temp.storage_errors,
                      ].map((err, i) => (
                        <p key={i} className="truncate">
                          {err}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const STAT_COLORS: Record<string, { border: string; bg: string; text: string }> = {
  amber: { border: "border-amber-200", bg: "bg-amber-50", text: "text-amber-600" },
  rose: { border: "border-rose-200", bg: ERROR_BG, text: ERROR_TEXT },
  red: { border: "border-red-200", bg: "bg-red-50", text: "text-red-600" },
};

function StatCard({ label, value, color }: { label: string; value: number; color?: string }) {
  const c = color ? STAT_COLORS[color] : undefined;

  return (
    <div
      className={`rounded-2xl border ${c?.border ?? "border-zinc-200"} ${c?.bg ?? "bg-white"} p-4 shadow-sm`}
    >
      <div className={`text-2xl font-black ${c?.text ?? "text-zinc-900"}`}>{value}</div>
      <p className="mt-1 text-[12px] font-medium tracking-widest text-zinc-400 uppercase">
        {label}
      </p>
    </div>
  );
}

function OrphanCategory({
  label,
  items,
}: {
  label: string;
  items: { id: number; storage_key: string; reason: string }[];
}) {
  if (items.length === 0) return null;

  return (
    <div>
      <p className="mb-1 text-[12px] font-bold text-zinc-500 uppercase">
        {label} ({items.length})
      </p>
      <div className="custom-scrollbar max-h-[100px] overflow-y-auto rounded-lg border border-zinc-100 bg-white">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between border-b border-zinc-50 px-3 py-1.5 last:border-0"
          >
            <span className="max-w-[180px] truncate font-mono text-[12px] text-zinc-600">
              {item.storage_key}
            </span>
            <span className="max-w-[120px] truncate text-[11px] text-zinc-400">{item.reason}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
