"use client";

import { useRouter } from "next/navigation";
import { BarChart3, Plus, Play } from "lucide-react";
import { SIDE_PANEL_CLASSES, SIDE_PANEL_LABEL } from "../ui/variants";

type Props = {
  columns: Record<string, { id: number; title: string; updated_at: string | null }[]>;
  total: number;
  isLoading: boolean;
};

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: "Draft", color: "bg-zinc-200 text-zinc-600" },
  in_prod: { label: "In Production", color: "bg-amber-100 text-amber-700" },
  rendered: { label: "Rendered", color: "bg-blue-100 text-blue-700" },
  published: { label: "Published", color: "bg-emerald-100 text-emerald-700" },
};

export default function HomeSecondaryPanel({ columns, total, isLoading }: Props) {
  const router = useRouter();

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
            {Object.entries(STATUS_LABELS).map(([key, { label, color }]) => (
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

      {/* Quick Actions */}
      <div className={SIDE_PANEL_CLASSES}>
        <span className={SIDE_PANEL_LABEL}>Quick Actions</span>
        <div className="space-y-2">
          <button
            onClick={() => router.push("/studio?new=true")}
            className="flex w-full items-center gap-2 rounded-lg bg-zinc-900 px-3 py-2 text-xs font-semibold text-white transition hover:bg-zinc-800"
          >
            <Plus className="h-3.5 w-3.5" />
            New Shorts
          </button>
          {columns.in_prod?.length > 0 && (
            <button
              onClick={() => router.push(`/studio?id=${columns.in_prod[0].id}`)}
              className="flex w-full items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-xs font-medium text-zinc-700 transition hover:bg-zinc-50"
            >
              <Play className="h-3.5 w-3.5" />
              Resume Last
            </button>
          )}
        </div>
      </div>
    </>
  );
}
