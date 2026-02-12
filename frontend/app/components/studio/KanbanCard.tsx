"use client";

import type { StoryboardListItem } from "../../hooks/useStudioKanban";

interface KanbanCardProps {
  item: StoryboardListItem;
  onClick: () => void;
}

export default function KanbanCard({ item, onClick }: KanbanCardProps) {
  const progress =
    item.scene_count > 0 ? Math.round((item.image_count / item.scene_count) * 100) : 0;
  const updatedLabel = item.updated_at ? formatRelativeTime(item.updated_at) : null;

  return (
    <button
      onClick={onClick}
      className="w-full rounded-xl border border-zinc-200 bg-white p-3 text-left transition hover:border-zinc-300 hover:shadow-sm"
    >
      {/* Title */}
      <h4 className="truncate text-xs font-semibold text-zinc-800">{item.title}</h4>

      {/* Progress bar */}
      {item.scene_count > 0 && (
        <div className="mt-2 flex items-center gap-2">
          <div className="h-1 flex-1 overflow-hidden rounded-full bg-zinc-100">
            <div
              className="h-full rounded-full bg-zinc-800 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-[11px] text-zinc-400 tabular-nums">
            {item.image_count}/{item.scene_count}
          </span>
        </div>
      )}

      {/* Footer: cast + timestamp */}
      <div className="mt-2 flex items-center justify-between">
        <div className="flex -space-x-1">
          {item.cast.slice(0, 3).map((c) => (
            <div
              key={c.id}
              className="flex h-5 w-5 items-center justify-center rounded-full border border-white bg-zinc-200 text-[11px] font-bold text-zinc-500"
              title={c.name}
            >
              {c.preview_url ? (
                <img
                  src={c.preview_url}
                  alt={c.name}
                  className="h-full w-full rounded-full object-cover"
                />
              ) : (
                c.name.charAt(0).toUpperCase()
              )}
            </div>
          ))}
        </div>
        {updatedLabel && <span className="text-[11px] text-zinc-400">{updatedLabel}</span>}
      </div>
    </button>
  );
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
