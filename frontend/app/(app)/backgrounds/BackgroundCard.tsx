"use client";

import { useRef } from "react";
import { Pencil, Trash2, Upload } from "lucide-react";
import type { Background } from "../../types";

type BackgroundCardProps = {
  background: Background;
  uploading: boolean;
  onEdit: (bg: Background) => void;
  onDelete: (bg: Background) => void;
  onUpload: (bgId: number, file: File) => void;
};

export default function BackgroundCard({
  background: bg,
  uploading,
  onEdit,
  onDelete,
  onUpload,
}: BackgroundCardProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const tags = bg.tags ?? [];
  const visibleTags = tags.slice(0, 5);
  const extraCount = tags.length - 5;

  return (
    <div className="group relative flex flex-col rounded-2xl border border-zinc-200/60 bg-white shadow-sm transition hover:shadow-md">
      {/* Thumbnail */}
      <div className="relative aspect-video w-full overflow-hidden rounded-t-2xl bg-zinc-100">
        {bg.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={bg.image_url}
            alt={bg.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-zinc-300">
            No image
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1.5 p-4">
        {/* Name + category */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-zinc-900">{bg.name}</span>
          {bg.category && (
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[9px] font-medium text-zinc-500">
              {bg.category}
            </span>
          )}
          {bg.is_system && (
            <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[9px] font-medium text-indigo-500">
              System
            </span>
          )}
        </div>

        {/* Description */}
        {bg.description && (
          <p className="line-clamp-2 text-xs text-zinc-500">{bg.description}</p>
        )}

        {/* Tags */}
        {visibleTags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {visibleTags.map((tag) => (
              <span
                key={tag}
                className="rounded bg-zinc-50 px-1.5 py-0.5 text-[10px] text-zinc-500"
              >
                {tag}
              </span>
            ))}
            {extraCount > 0 && (
              <span className="rounded bg-zinc-50 px-1.5 py-0.5 text-[10px] text-zinc-400">
                +{extraCount} more
              </span>
            )}
          </div>
        )}

        {/* Footer: weight + actions */}
        <div className="mt-auto flex items-center justify-between pt-1">
          <span className="text-[10px] text-zinc-400">
            weight: {bg.weight.toFixed(2)}
          </span>
          <div className="flex items-center gap-1.5">
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onUpload(bg.id, f);
                e.target.value = "";
              }}
            />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="rounded-full border border-zinc-200 p-1.5 text-zinc-500 transition hover:bg-zinc-100 disabled:opacity-40"
              title="Upload image"
            >
              <Upload className="h-3 w-3" />
            </button>
            <button
              onClick={() => onEdit(bg)}
              className="rounded-full border border-zinc-200 p-1.5 text-zinc-500 transition hover:bg-zinc-100"
              title="Edit"
            >
              <Pencil className="h-3 w-3" />
            </button>
            {!bg.is_system && (
              <button
                onClick={() => onDelete(bg)}
                className="rounded-full border border-red-200 p-1.5 text-red-400 transition hover:bg-red-50"
                title="Delete"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
