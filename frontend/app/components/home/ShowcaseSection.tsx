"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, Clapperboard, Loader2, Play, Sparkles } from "lucide-react";
import Link from "next/link";
import type { RenderHistoryItem } from "../../types";
import { useUIStore } from "../../store/useUIStore";
import { formatRelativeTime } from "../../utils/format";
import { API_BASE } from "../../constants";

const DISPLAY_COUNT = 30;
const EXPANDED_LIMIT = 50;
const PER_GROUP_LIMIT = 8;

const LABEL_DISPLAY: Record<string, string> = {
  full: "Full Video",
  post: "Post Format",
  single: "Single",
};

export default function ShowcaseSection() {
  const [items, setItems] = useState<RenderHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedVideo, setSelectedVideo] = useState<RenderHistoryItem | null>(null);
  const [expanded, setExpanded] = useState(false);

  const fetchHistory = useCallback(async (limit: number) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/video/render-history?offset=0&limit=${limit}`);
      if (!res.ok) throw new Error("fetch failed");
      const data = await res.json();
      setItems(Array.isArray(data.items) ? data.items : []);
      setTotal(data.total);
    } catch {
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory(DISPLAY_COUNT);
  }, [fetchHistory]);

  const handleToggleExpand = () => {
    if (!expanded) {
      fetchHistory(EXPANDED_LIMIT);
    }
    setExpanded(!expanded);
  };

  const groupedItems = useMemo(() => {
    const groups: Record<string, RenderHistoryItem[]> = {};
    for (const v of items) {
      const key = v.label || "other";
      if (!groups[key]) groups[key] = [];
      groups[key].push(v);
    }
    return groups;
  }, [items]);

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-zinc-200 bg-white p-8">
        <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/50 p-8 text-center">
        <div className="mb-3 inline-flex rounded-full bg-zinc-100 p-3">
          <Sparkles className="h-6 w-6 text-zinc-400" />
        </div>
        <h3 className="mb-1 text-sm font-semibold text-zinc-900">Your Showcase Awaits</h3>
        <p className="mb-4 text-xs text-zinc-500">Create your first video to see it here</p>
        <button
          onClick={() => {
            useUIStore.getState().set({ showSetupWizard: true, setupWizardInitialStep: 1 });
          }}
          className="inline-flex items-center gap-2 rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-zinc-800"
        >
          <Clapperboard className="h-3.5 w-3.5" />
          Start Creating
        </button>
      </div>
    );
  }

  return (
    <>
      <div>
        {/* Header */}
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-amber-500" />
            <h2 className="text-sm font-semibold text-zinc-900">Video Gallery</h2>
            <span className="text-xs text-zinc-400">({total})</span>
          </div>
          {total > DISPLAY_COUNT && (
            <button
              onClick={handleToggleExpand}
              className="text-xs font-medium text-zinc-500 transition hover:text-zinc-700"
            >
              {expanded ? "Show Less" : "View All"}
            </button>
          )}
        </div>

        {/* Rows by type */}
        <div className="space-y-4">
          {Object.entries(groupedItems).map(([label, videos]) => (
            <div key={label}>
              <div className="mb-2 flex items-center gap-2">
                <span className="text-xs font-medium text-zinc-600">
                  {LABEL_DISPLAY[label] || label}
                </span>
                <span className="text-[11px] text-zinc-400">({videos.length})</span>
              </div>
              <div
                className={
                  expanded
                    ? "scrollbar-hide flex gap-3 overflow-x-auto pb-2"
                    : "flex flex-wrap gap-3"
                }
              >
                {(expanded ? videos : videos.slice(0, PER_GROUP_LIMIT)).map((video) => (
                  <button
                    key={video.id}
                    onClick={() => setSelectedVideo(video)}
                    className="group w-[160px] shrink-0 overflow-hidden rounded-xl border border-zinc-200 bg-white text-left transition hover:border-zinc-300 hover:shadow-md"
                  >
                    <div className="relative h-[204px] w-full overflow-hidden bg-zinc-900">
                      <video
                        src={video.url}
                        className="h-full w-full object-cover"
                        muted
                        playsInline
                      />
                      <div className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 transition group-hover:opacity-100">
                        <div className="rounded-full bg-white/90 p-2">
                          <Play className="h-4 w-4 text-zinc-900" />
                        </div>
                      </div>
                    </div>
                    <div className="px-2 py-1.5">
                      <p className="truncate text-xs font-medium text-zinc-900">
                        {video.storyboard_title || video.project_name || "Video"}
                      </p>
                      <p className="text-[11px] text-zinc-400">
                        {formatRelativeTime(video.created_at)}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Video Preview Modal */}
      {selectedVideo && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setSelectedVideo(null)}
        >
          <div
            className="w-full max-w-md rounded-2xl bg-white p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold text-zinc-900">
                  {selectedVideo.storyboard_title || selectedVideo.project_name || "Video"}
                </h2>
                <p className="mt-1 text-sm text-zinc-500">
                  {formatRelativeTime(selectedVideo.created_at)}
                </p>
              </div>
              <button
                onClick={() => setSelectedVideo(null)}
                className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
              >
                &#x2715;
              </button>
            </div>

            <div
              className="mb-4 overflow-hidden rounded-lg bg-zinc-900"
              style={{ aspectRatio: "9/16" }}
            >
              <video
                src={selectedVideo.url}
                className="h-full w-full object-contain"
                controls
                autoPlay
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-600">
                  {selectedVideo.label === "full" ? "Full Video" : "Post Format"}
                </span>
                {selectedVideo.group_name && (
                  <>
                    <span className="text-zinc-300">&bull;</span>
                    <span className="text-xs text-zinc-500">{selectedVideo.group_name}</span>
                  </>
                )}
              </div>
              <Link
                href={`/studio?id=${selectedVideo.storyboard_id}`}
                className="inline-flex items-center gap-1 text-xs font-medium text-zinc-500 transition hover:text-zinc-900"
                onClick={() => setSelectedVideo(null)}
              >
                Storyboard
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
