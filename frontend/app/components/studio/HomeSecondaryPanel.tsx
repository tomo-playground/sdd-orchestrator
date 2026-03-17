"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { BarChart3, Clock } from "lucide-react";
import { SIDE_PANEL_CLASSES, SIDE_PANEL_LABEL } from "../ui/variants";
import { formatRelativeTime } from "../../utils/format";

type Props = {
  columns: Record<string, { id: number; title: string; updated_at: string | null }[]>;
  total: number;
  isLoading: boolean;
};

const STATUS_META: Record<string, { label: string; color: string; dot: string }> = {
  draft: { label: "초안", color: "bg-zinc-200 text-zinc-600", dot: "bg-zinc-400" },
  in_prod: { label: "제작 중", color: "bg-amber-100 text-amber-700", dot: "bg-amber-400" },
  rendered: { label: "렌더 완료", color: "bg-blue-100 text-blue-700", dot: "bg-blue-400" },
  published: {
    label: "게시됨",
    color: "bg-emerald-100 text-emerald-700",
    dot: "bg-emerald-400",
  },
};

const MAX_RECENT = 3;

export default function HomeSecondaryPanel({ columns, total, isLoading }: Props) {
  const router = useRouter();

  const recentItems = useMemo(() => {
    const all: { id: number; title: string; updated_at: string; status: string }[] = [];
    for (const [status, items] of Object.entries(columns)) {
      for (const item of items) {
        if (item.updated_at) all.push({ ...item, updated_at: item.updated_at, status });
      }
    }
    all.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
    return all.slice(0, MAX_RECENT);
  }, [columns]);

  return (
    <>
      {/* Quick Stats */}
      <div className={SIDE_PANEL_CLASSES}>
        <span className={SIDE_PANEL_LABEL}>
          <BarChart3 className="mr-1 inline h-3 w-3" />
          Quick Stats
        </span>
        {isLoading ? (
          <p className="text-xs text-zinc-400">Loading...</p>
        ) : (
          <div className="space-y-1.5">
            {Object.entries(STATUS_META).map(([key, { label, color }]) => (
              <div key={key} className="flex items-center justify-between text-xs">
                <span className={`rounded-full px-2 py-0.5 font-medium ${color}`}>{label}</span>
                <span className="font-semibold text-zinc-700">{columns[key]?.length ?? 0}</span>
              </div>
            ))}
            <div className="flex items-center justify-between border-t border-zinc-100 pt-1.5 text-xs">
              <span className="text-zinc-500">Total</span>
              <span className="font-bold text-zinc-900">{total}</span>
            </div>
          </div>
        )}
      </div>

      {/* Recently Updated */}
      {!isLoading && recentItems.length > 0 && (
        <div className={SIDE_PANEL_CLASSES}>
          <span className={SIDE_PANEL_LABEL}>
            <Clock className="mr-1 inline h-3 w-3" />
            Recently Updated
          </span>
          <div className="space-y-1">
            {recentItems.map((item) => (
              <button
                key={item.id}
                onClick={() => router.push(`/studio?id=${item.id}`)}
                className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition hover:bg-zinc-50"
              >
                <span
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${STATUS_META[item.status]?.dot ?? "bg-zinc-300"}`}
                />
                <span className="min-w-0 flex-1 truncate text-xs font-medium text-zinc-700">
                  {item.title || "Untitled"}
                </span>
                <span className="shrink-0 text-[11px] text-zinc-400">
                  {formatRelativeTime(item.updated_at)}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
