"use client";

import { useState } from "react";
import { Image, Loader2, RefreshCw, CheckCircle2, AlertCircle, Pencil, X } from "lucide-react";
import Button from "../ui/Button";
import type { StageLocationStatus } from "../../types";

export default function StageLocationCard({
  location,
  isRegenerating,
  onRegenerate,
}: {
  location: StageLocationStatus;
  isRegenerating: boolean;
  onRegenerate: (tags?: string[]) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTags, setEditTags] = useState("");

  const startEdit = () => {
    setEditTags(location.tags.join(", "));
    setIsEditing(true);
  };

  const cancelEdit = () => setIsEditing(false);

  const saveAndRegenerate = () => {
    const tags = editTags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    setIsEditing(false);
    onRegenerate(tags);
  };

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
      {/* Image area */}
      <div className="relative aspect-video bg-zinc-100">
        {location.has_image && location.image_url ? (
          <img
            src={location.image_url}
            alt={location.location_key}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Image className="h-8 w-8 text-zinc-300" />
          </div>
        )}
        {isRegenerating && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40">
            <Loader2 className="h-6 w-6 animate-spin text-white" />
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-900">
            {location.location_key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </h3>
          {location.has_image ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          ) : (
            <AlertCircle className="h-4 w-4 text-zinc-300" />
          )}
        </div>

        {/* Tags — read or edit mode */}
        {isEditing ? (
          <div className="mb-2">
            <input
              type="text"
              value={editTags}
              onChange={(e) => setEditTags(e.target.value)}
              className="w-full rounded-lg border border-zinc-300 px-2 py-1.5 text-xs text-zinc-700 outline-none focus:border-zinc-500"
              placeholder="classroom, desk, window"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") saveAndRegenerate();
                if (e.key === "Escape") cancelEdit();
              }}
            />
            <div className="mt-1.5 flex gap-1">
              <Button
                size="sm"
                className="flex-1"
                onClick={saveAndRegenerate}
                disabled={isRegenerating}
              >
                <RefreshCw className="h-3 w-3" />
                Save & Regenerate
              </Button>
              <button
                onClick={cancelEdit}
                className="rounded-lg p-1.5 text-zinc-400 hover:text-zinc-600"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        ) : (
          <div className="group mb-2 flex flex-wrap items-center gap-1">
            {location.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-600"
              >
                {tag}
              </span>
            ))}
            <button
              onClick={startEdit}
              className="rounded p-0.5 text-zinc-300 opacity-0 transition group-hover:opacity-100 hover:text-zinc-500"
              title="Edit tags"
            >
              <Pencil className="h-3 w-3" />
            </button>
          </div>
        )}

        {/* Scene count */}
        <p className="mb-2 text-[11px] text-zinc-400">
          {location.scene_ids.length} scene{location.scene_ids.length !== 1 ? "s" : ""}
        </p>

        {/* Actions */}
        {!isEditing && (
          <Button
            size="sm"
            variant="outline"
            className="w-full"
            onClick={() => onRegenerate()}
            loading={isRegenerating}
            disabled={isRegenerating}
          >
            <RefreshCw className="h-3 w-3" />
            {location.has_image ? "Regenerate" : "Generate"}
          </Button>
        )}
      </div>
    </div>
  );
}
