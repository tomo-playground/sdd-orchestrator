"use client";

import type { RecentVideo } from "../../types";
import { cx, SECTION_CLASSES, ERROR_ICON } from "../ui/variants";
import { formatRelativeTime } from "../../utils/format";

type RenderedVideosSectionProps = {
  videoUrl: string | null;
  videoUrlFull: string | null;
  videoUrlPost: string | null;
  recentVideos: RecentVideo[];
  uploadedMap?: Map<string, string>;
  onVideoPreview: (url: string) => void;
  onDeleteRecentVideo: (url: string) => void;
  onUploadToYouTube?: (videoUrl: string, renderHistoryId?: number) => void;
  compact?: boolean;
  variant?: "card" | "list";
};

const YT_ICON = (
  <svg viewBox="0 0 24 24" className="h-3 w-3 fill-current">
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
  </svg>
);

export default function RenderedVideosSection({
  videoUrl,
  videoUrlFull,
  videoUrlPost,
  recentVideos,
  uploadedMap,
  onVideoPreview,
  onDeleteRecentVideo,
  onUploadToYouTube,
  compact = false,
  variant = "card",
}: RenderedVideosSectionProps) {
  if (!videoUrl && !videoUrlFull && !videoUrlPost && recentVideos.length === 0) {
    return null;
  }

  if (variant === "list") {
    return (
      <section className="grid gap-2">
        <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Recent ({recentVideos.length})
        </span>
        {recentVideos.length === 0 && <p className="text-xs text-zinc-400">No videos yet.</p>}
        {recentVideos.map((item, idx) => {
          const ytVideoId = uploadedMap?.get(item.url);
          const isUploaded = !!ytVideoId;
          return (
            <div
              key={`${item.url}-${item.createdAt}`}
              className={cx(
                "flex items-center gap-2.5 rounded-xl border px-2.5 py-2 transition hover:bg-zinc-50",
                idx === 0 ? "border-zinc-300 bg-white" : "border-zinc-200 bg-white/70"
              )}
            >
              <button
                type="button"
                onClick={() => onVideoPreview(item.url)}
                className="h-10 w-10 flex-shrink-0 overflow-hidden rounded-lg bg-black"
              >
                <video
                  muted
                  playsInline
                  preload="metadata"
                  src={item.url}
                  className="pointer-events-none h-full w-full object-cover"
                />
              </button>
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="text-xs font-semibold text-zinc-700 uppercase">{item.label}</span>
                <span className="text-[11px] text-zinc-400">
                  {formatRelativeTime(item.createdAt)}
                </span>
              </div>
              <div className="flex flex-shrink-0 items-center gap-1">
                {onUploadToYouTube && !isUploaded && (
                  <button
                    type="button"
                    onClick={() => onUploadToYouTube(item.url, item.renderHistoryId)}
                    className="rounded-md bg-red-600 p-1 text-white transition hover:bg-red-700"
                    title="Upload to YouTube"
                  >
                    {YT_ICON}
                  </button>
                )}
                {isUploaded && (
                  <a
                    href={`https://studio.youtube.com/video/${ytVideoId}/edit`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-md border border-zinc-200 bg-zinc-50 p-1 text-zinc-500 transition hover:bg-zinc-100"
                    title="YouTube Studio"
                  >
                    {YT_ICON}
                  </a>
                )}
                <button
                  type="button"
                  onClick={() => onDeleteRecentVideo(item.url)}
                  className="rounded-md p-1 text-zinc-400 transition hover:text-red-500"
                  title="Delete"
                >
                  <svg viewBox="0 0 16 16" className="h-3 w-3 fill-current">
                    <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z" />
                    <path
                      fillRule="evenodd"
                      d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H5.5l1-1h3l1 1H13a1 1 0 0 1 1 1v1z"
                    />
                  </svg>
                </button>
              </div>
            </div>
          );
        })}
      </section>
    );
  }

  return (
    <section className={cx(compact ? "" : SECTION_CLASSES, "grid gap-4")}>
      {!compact && (
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">Preview</h2>
          <p className="text-xs text-zinc-500">
            {videoUrlFull || videoUrlPost ? "Compare full and post renders." : "Latest render."}
          </p>
        </div>
      )}
      {recentVideos.length > 0 && (
        <div className="grid gap-3">
          <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Recent ({recentVideos.length})
          </span>
          <div
            className={
              compact ? "grid grid-cols-1 gap-4" : "grid gap-4 md:grid-cols-2 lg:grid-cols-4"
            }
          >
            {recentVideos.map((item, idx) => {
              const ytVideoId = uploadedMap?.get(item.url);
              const isUploaded = !!ytVideoId;
              return (
                <div
                  key={`${item.url}-${item.createdAt}`}
                  className={`group grid gap-2 rounded-2xl border bg-white/70 p-3 shadow-sm ${
                    idx === 0
                      ? "border-zinc-900/40 bg-white shadow-lg ring-2 shadow-zinc-900/10 ring-zinc-900/10"
                      : "border-zinc-200"
                  }`}
                >
                  <div className="grid gap-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                        {item.label}
                      </span>
                      {/* Project Badge */}
                      {item.projectName && (
                        <span
                          className="max-w-[120px] truncate rounded-full border border-zinc-200 bg-zinc-50 px-1.5 py-px text-[11px] font-medium text-zinc-600"
                          title={`Project: ${item.projectName}`}
                        >
                          {item.projectName}
                        </span>
                      )}
                      {idx === 0 && (
                        <span className="rounded-full bg-emerald-50 px-1.5 py-px text-[11px] font-bold text-emerald-600 uppercase">
                          New
                        </span>
                      )}
                      {isUploaded && (
                        <span className="rounded-full bg-red-50 px-1.5 py-px text-[11px] font-bold text-red-500">
                          YT
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-zinc-400">
                      {new Date(item.createdAt).toLocaleString()}
                    </span>
                  </div>
                  <div className="aspect-[9/16] w-full overflow-hidden rounded-2xl bg-black shadow">
                    <button
                      type="button"
                      onClick={() => onVideoPreview(item.url)}
                      className="h-full w-full"
                    >
                      <video
                        muted
                        playsInline
                        preload="metadata"
                        src={item.url}
                        className="pointer-events-none h-full w-full object-cover"
                      />
                    </button>
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    {onUploadToYouTube && !isUploaded && (
                      <button
                        type="button"
                        onClick={() => onUploadToYouTube(item.url, item.renderHistoryId)}
                        className="flex items-center gap-1 rounded-md bg-red-600 px-2 py-1 text-[12px] font-semibold text-white transition hover:bg-red-700"
                        title="Upload to YouTube"
                      >
                        {YT_ICON}
                        Upload
                      </button>
                    )}
                    {isUploaded && (
                      <a
                        href={`https://studio.youtube.com/video/${ytVideoId}/edit`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 text-[12px] font-medium text-zinc-600 transition hover:bg-zinc-100"
                      >
                        {YT_ICON}
                        Studio
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={() => onDeleteRecentVideo(item.url)}
                      className={`ml-auto text-[12px] font-medium text-zinc-400 transition hover:${ERROR_ICON}`}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      {recentVideos.length === 0 && (
        <div className="rounded-2xl border border-dashed border-zinc-200 bg-white/70 p-4 text-xs text-zinc-500">
          No rendered videos yet. Run a render to see results here.
        </div>
      )}
    </section>
  );
}
