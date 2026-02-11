"use client";

import { useEffect, useState } from "react";
import { format } from "date-fns";
import { FileText, X } from "lucide-react";
import type { StoryboardListItem } from "../../types";

type StoryboardCardProps = {
  sb: StoryboardListItem;
  onClick: () => void;
  onDelete?: () => void;
};

export default function StoryboardCard({ sb, onClick, onDelete }: StoryboardCardProps) {
  return (
    <div
      data-testid={`storyboard-card-${sb.id}`}
      className="group relative flex h-full cursor-pointer flex-col gap-2 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm transition hover:shadow-md"
      onClick={onClick}
    >
      <h3 className="line-clamp-1 text-sm font-semibold text-zinc-900">{sb.title}</h3>
      {sb.description && <p className="line-clamp-2 text-xs text-zinc-500">{sb.description}</p>}
      <div className="flex items-center gap-3 text-[12px] text-zinc-400">
        <span>{sb.scene_count} scenes</span>
        <span className={sb.image_count === 0 ? "text-amber-500" : ""}>
          {sb.image_count} images
        </span>
        {sb.updated_at && <span>{format(new Date(sb.updated_at), "yyyy.MM.dd")}</span>}
      </div>
      {/* Cast thumbnails */}
      {sb.cast && sb.cast.length > 0 && (
        <div className="mt-auto flex items-center gap-1 pt-1">
          {sb.cast.map((c, i) => (
            <div
              key={`${c.id}-${i}`}
              title={`${c.speaker}: ${c.name}`}
              className="h-6 w-6 shrink-0 overflow-hidden rounded-full border border-zinc-200 bg-zinc-100"
            >
              {c.preview_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={c.preview_url}
                  alt={c.name}
                  className="h-full w-full object-cover object-top"
                />
              ) : (
                <span className="flex h-full w-full items-center justify-center text-[8px] text-zinc-400">
                  {c.speaker}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
      {onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="absolute top-3 right-3 text-zinc-300 opacity-0 transition group-hover:opacity-100 hover:text-red-400"
          title="Delete"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}

export function DraftCard({ onClick }: { onClick: () => void }) {
  const [hasDraft, setHasDraft] = useState(false);

  useEffect(() => {
    try {
      const stored =
        localStorage.getItem("shorts-producer:studio:v1") ||
        localStorage.getItem("shorts-producer:draft:v1");
      if (stored) {
        const data = JSON.parse(stored);
        const state = data?.state || data;
        if (state?.topic || (state?.scenes && state.scenes.length > 0)) {
          setHasDraft(true); // eslint-disable-line react-hooks/set-state-in-effect
        }
      }
    } catch {}
  }, []);

  if (!hasDraft) return null;

  return (
    <div
      onClick={onClick}
      className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-zinc-300 bg-zinc-50 p-4 text-center transition hover:border-zinc-400 hover:bg-zinc-100/50"
    >
      <FileText className="h-5 w-5 text-zinc-400" />
      <span className="text-xs font-semibold text-zinc-600">Continue Draft</span>
      <span className="text-[12px] text-zinc-400">Resume your unsaved work</span>
    </div>
  );
}
