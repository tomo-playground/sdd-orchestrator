"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, Clapperboard, Loader2, Play, Sparkles } from "lucide-react";
import type { ProjectItem, RenderHistoryItem } from "../../types";
import { useUIStore } from "../../store/useUIStore";

const PAGE_SIZE = 12;

export default function ShowcaseSection() {
  const [items, setItems] = useState<RenderHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<RenderHistoryItem | null>(null);

  // Project filter
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  // Fetch projects for filter dropdown
  useEffect(() => {
    fetch("/api/projects")
      .then((r) => r.json())
      .then((data) => setProjects(Array.isArray(data) ? data : []))
      .catch(() => setProjects([]));
  }, []);

  // Fetch render history
  const fetchHistory = useCallback(
    async (newOffset: number, append: boolean) => {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      try {
        const params = new URLSearchParams({
          offset: String(newOffset),
          limit: String(PAGE_SIZE),
        });
        if (selectedProjectId !== null) {
          params.set("project_id", String(selectedProjectId));
        }
        const res = await fetch(`/api/video/render-history?${params}`);
        if (!res.ok) throw new Error("fetch failed");
        const data = await res.json();
        const fetched = Array.isArray(data.items) ? data.items : [];
        setItems((prev) => (append ? [...prev, ...fetched] : fetched));
        setTotal(data.total);
        setOffset(newOffset);
      } catch {
        if (!append) {
          setItems([]);
          setTotal(0);
        }
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [selectedProjectId]
  );

  useEffect(() => {
    fetchHistory(0, false);
  }, [fetchHistory]);

  const handleLoadMore = () => {
    const nextOffset = offset + PAGE_SIZE;
    if (nextOffset < total) fetchHistory(nextOffset, true);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  // Loading state
  if (loading) {
    return (
      <div className="mb-8 flex items-center justify-center rounded-2xl border border-zinc-200 bg-white p-12">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  // Empty state
  if (items.length === 0 && !loading) {
    return (
      <div className="mb-8 rounded-2xl border border-dashed border-zinc-200 bg-zinc-50/50 p-12 text-center">
        <div className="mb-4 inline-flex rounded-full bg-zinc-100 p-4">
          <Sparkles className="h-8 w-8 text-zinc-400" />
        </div>
        <h3 className="mb-2 text-lg font-semibold text-zinc-900">Your Showcase Awaits</h3>
        <p className="mb-6 text-sm text-zinc-500">
          Create your first video to see it featured here
        </p>
        <button
          onClick={() => {
            if (projects.length > 0) {
              window.location.href = "/studio";
            } else {
              useUIStore.getState().set({ showSetupWizard: true, setupWizardInitialStep: 1 });
            }
          }}
          className="inline-flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800"
        >
          <Clapperboard className="h-4 w-4" />
          Start Creating
        </button>
      </div>
    );
  }

  const hasMore = offset + PAGE_SIZE < total;

  return (
    <>
      <div className="mb-8">
        {/* Header + Project Filter */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-amber-500" />
            <h2 className="text-xl font-bold text-zinc-900">Video Gallery</h2>
            <span className="ml-1 text-sm text-zinc-400">({total})</span>
          </div>

          {projects.length > 1 && (
            <div className="relative">
              <select
                value={selectedProjectId ?? ""}
                onChange={(e) =>
                  setSelectedProjectId(e.target.value ? Number(e.target.value) : null)
                }
                className="appearance-none rounded-lg border border-zinc-200 bg-white py-1.5 pr-8 pl-3 text-sm text-zinc-700 transition hover:border-zinc-300 focus:border-zinc-400 focus:outline-none"
              >
                <option value="">All Projects</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute top-1/2 right-2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            </div>
          )}
        </div>

        <p className="mb-6 text-sm text-zinc-500">Your rendered videos</p>

        {/* Video Grid */}
        <div
          className="grid gap-4"
          style={{ gridTemplateColumns: "repeat(auto-fill, minmax(225px, 1fr))" }}
        >
          {items.map((video) => (
            <button
              key={video.id}
              onClick={() => setSelectedVideo(video)}
              className="group relative overflow-hidden rounded-xl border border-zinc-200 bg-white text-left transition hover:border-zinc-300 hover:shadow-md"
            >
              <div
                className="relative w-full overflow-hidden bg-zinc-900"
                style={{ aspectRatio: "9/16", maxHeight: "400px" }}
              >
                <video src={video.url} className="h-full w-full object-cover" muted playsInline />
                <div className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 transition group-hover:opacity-100">
                  <div className="rounded-full bg-white/90 p-3">
                    <Play className="h-6 w-6 text-zinc-900" />
                  </div>
                </div>
              </div>

              <div className="p-4">
                <h3 className="mb-1 truncate font-semibold text-zinc-900">
                  {video.storyboard_title || video.project_name || formatDate(video.created_at)}
                </h3>
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                  <span className="rounded-full bg-zinc-100 px-2 py-0.5 font-medium">
                    {video.label === "full" ? "Full" : "Post"}
                  </span>
                  <span>{formatDate(video.created_at)}</span>
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Load More */}
        {hasMore && (
          <div className="mt-6 flex justify-center">
            <button
              onClick={handleLoadMore}
              disabled={loadingMore}
              className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 transition hover:border-zinc-300 hover:bg-zinc-50 disabled:opacity-50"
            >
              {loadingMore ? <Loader2 className="h-4 w-4 animate-spin" /> : "Load More"}
            </button>
          </div>
        )}
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
                <p className="mt-1 text-sm text-zinc-500">{formatDate(selectedVideo.created_at)}</p>
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
          </div>
        </div>
      )}
    </>
  );
}
