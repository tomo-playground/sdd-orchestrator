"use client";

import { useTrashTab, type TrashItem, type FilterType } from "../hooks/useTrashTab";
import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import { FILTER_PILL_ACTIVE } from "../../../components/ui/variants";

const RETENTION_DAYS = 30;

function daysRemaining(deletedAt: string): number {
  const deleted = new Date(deletedAt);
  const now = new Date();
  const diff = RETENTION_DAYS - Math.floor((now.getTime() - deleted.getTime()) / 86_400_000);
  return Math.max(0, diff);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

const TYPE_BADGE: Record<TrashItem["type"], { label: string; color: string }> = {
  storyboard: { label: "Storyboard", color: "bg-blue-100 text-blue-700" },
  character: { label: "Character", color: "bg-purple-100 text-purple-700" },
  prompt_history: { label: "Prompt", color: "bg-amber-100 text-amber-700" },
};

export default function TrashTab() {
  const { confirm, dialogProps } = useConfirm();

  const { items, filter, setFilter, loading, filtered, handleRestore, handlePermanentDelete } =
    useTrashTab(confirm);

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-base font-bold tracking-tight">Trash</h2>

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2">
        {(["all", "storyboard", "character", "prompt_history"] as FilterType[]).map((f) => {
          const labels: Record<FilterType, string> = {
            all: "All",
            storyboard: "Storyboards",
            character: "Characters",
            prompt_history: "Prompts",
          };
          const count = f === "all" ? items.length : items.filter((i) => i.type === f).length;
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                filter === f
                  ? FILTER_PILL_ACTIVE
                  : "border border-zinc-200 bg-white text-zinc-500 hover:bg-zinc-50"
              }`}
            >
              {labels[f]} ({count})
            </button>
          );
        })}
      </div>

      {/* List */}
      {loading ? (
        <p className="py-8 text-center text-sm text-zinc-400">Loading...</p>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-zinc-400">
          <span className="text-3xl">&#128465;</span>
          <p className="text-sm">Trash is empty</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {filtered.map((item) => {
            const badge = TYPE_BADGE[item.type];
            const remaining = daysRemaining(item.deleted_at);
            return (
              <div
                key={`${item.type}-${item.id}`}
                className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-4 py-3"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-[12px] font-semibold ${badge.color}`}
                  >
                    {badge.label}
                  </span>
                  <span className="truncate text-sm font-medium text-zinc-800">
                    {item.name || "Untitled"}
                  </span>
                  <span className="shrink-0 text-[13px] text-zinc-400">
                    {formatDate(item.deleted_at)}
                  </span>
                  <span className="shrink-0 text-[13px] text-zinc-400">{remaining}d left</span>
                </div>

                <div className="ml-3 flex shrink-0 gap-2">
                  <button
                    onClick={() => handleRestore(item)}
                    className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 transition hover:bg-zinc-50"
                  >
                    Restore
                  </button>
                  <button
                    onClick={() => handlePermanentDelete(item)}
                    className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-100"
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
      <ConfirmDialog {...dialogProps} />
    </section>
  );
}
