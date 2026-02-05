"use client";

import type { RecentVideo } from "../../types";
import { cx, SECTION_CLASSES } from "../ui/variants";

type RenderedVideosSectionProps = {
  videoUrl: string | null;
  videoUrlFull: string | null;
  videoUrlPost: string | null;
  recentVideos: RecentVideo[];
  uploadedMap?: Map<string, string>;
  onVideoPreview: (url: string) => void;
  onDeleteRecentVideo: (url: string) => void;
  onUploadToYouTube?: (videoUrl: string, renderHistoryId?: number) => void;
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
}: RenderedVideosSectionProps) {
  if (!videoUrl && !videoUrlFull && !videoUrlPost && recentVideos.length === 0) {
    return null;
  }

  return (
    <section className={cx(SECTION_CLASSES, "grid gap-4")}>
      <div>
        <h2 className="text-lg font-semibold text-zinc-900">Preview</h2>
        <p className="text-xs text-zinc-500">
          {videoUrlFull || videoUrlPost
            ? "Compare full and post renders."
            : "Latest render."}
        </p>
      </div>
      {recentVideos.length > 0 && (
        <div className="grid gap-3">
          <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Recent (8)
          </span>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
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
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                        {item.label}
                      </span>
                      {idx === 0 && (
                        <span className="rounded-full bg-emerald-50 px-1.5 py-px text-[8px] font-bold text-emerald-600 uppercase">
                          New
                        </span>
                      )}
                      {isUploaded && (
                        <span className="rounded-full bg-red-50 px-1.5 py-px text-[8px] font-bold text-red-500">
                          YT
                        </span>
                      )}
                    </div>
                    <span className="text-[9px] text-zinc-400">
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
                        className="flex items-center gap-1 rounded-md bg-red-600 px-2 py-1 text-[10px] font-semibold text-white transition hover:bg-red-700"
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
                        className="flex items-center gap-1 rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 text-[10px] font-medium text-zinc-600 transition hover:bg-zinc-100"
                      >
                        {YT_ICON}
                        Studio
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={() => onDeleteRecentVideo(item.url)}
                      className="ml-auto text-[10px] font-medium text-zinc-400 transition hover:text-rose-500"
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
