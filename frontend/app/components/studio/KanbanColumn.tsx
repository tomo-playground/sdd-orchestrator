"use client";

import type { StoryboardListItem } from "../../hooks/useStudioKanban";
import KanbanCard from "./KanbanCard";

const COLUMN_META: Record<string, { label: string; icon: string }> = {
  draft: { label: "초안", icon: "📝" },
  in_prod: { label: "제작 중", icon: "🎨" },
  rendered: { label: "렌더 완료", icon: "🎬" },
  published: { label: "게시됨", icon: "📺" },
};

interface KanbanColumnProps {
  status: string;
  items: StoryboardListItem[];
  onCardClick: (id: number) => void;
  onCardDelete?: (id: number) => void;
}

export default function KanbanColumn({ status, items, onCardClick, onCardDelete }: KanbanColumnProps) {
  const meta = COLUMN_META[status] ?? { label: status, icon: "📋" };

  return (
    <div className="flex min-h-[200px] flex-col">
      {/* Column Header */}
      <div className="mb-3 flex items-center gap-1.5">
        <span className="text-sm">{meta.icon}</span>
        <span className="text-[13px] font-semibold text-zinc-600">{meta.label}</span>
        <span className="ml-auto rounded-full bg-zinc-100 px-1.5 py-0.5 text-[11px] font-bold text-zinc-400 tabular-nums">
          {items.length}
        </span>
      </div>

      {/* Cards */}
      <div className="flex flex-1 flex-col gap-2">
        {items.length === 0 ? (
          <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-zinc-200 p-4">
            <span className="text-[12px] text-zinc-300">항목 없음</span>
          </div>
        ) : (
          items.map((item) => (
            <KanbanCard key={item.id} item={item} onClick={() => onCardClick(item.id)} onDelete={onCardDelete} />
          ))
        )}
      </div>
    </div>
  );
}
