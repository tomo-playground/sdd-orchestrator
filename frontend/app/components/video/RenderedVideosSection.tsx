"use client";

type RecentVideo = {
  url: string;
  label: "full" | "post" | "single";
  createdAt: number;
};

type RenderedVideosSectionProps = {
  videoUrl: string | null;
  videoUrlFull: string | null;
  videoUrlPost: string | null;
  recentVideos: RecentVideo[];
  onVideoPreview: (url: string) => void;
  onDeleteRecentVideo: (url: string) => void;
};

export default function RenderedVideosSection({
  videoUrl,
  videoUrlFull,
  videoUrlPost,
  recentVideos,
  onVideoPreview,
  onDeleteRecentVideo,
}: RenderedVideosSectionProps) {
  if (!videoUrl && !videoUrlFull && !videoUrlPost && recentVideos.length === 0) {
    return null;
  }

  return (
    <section className="grid gap-4 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-slate-200/40">
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
            {recentVideos.map((item, idx) => (
              <div
                key={`${item.url}-${item.createdAt}`}
                className={`group grid gap-2 rounded-2xl border bg-white/70 p-3 shadow-sm ${
                  idx === 0
                    ? "border-zinc-900/40 bg-white shadow-lg ring-2 shadow-zinc-900/10 ring-zinc-900/10"
                    : "border-zinc-200"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    {item.label}
                  </span>
                  <span className="text-[10px] text-zinc-400">
                    {new Date(item.createdAt).toLocaleString()}
                  </span>
                  {idx === 0 && (
                    <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[9px] font-semibold tracking-[0.2em] text-emerald-600 uppercase">
                      Latest
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => onDeleteRecentVideo(item.url)}
                    className="text-[10px] font-semibold tracking-[0.2em] text-rose-500 uppercase opacity-0 transition group-hover:opacity-100"
                  >
                    Delete
                  </button>
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
              </div>
            ))}
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
