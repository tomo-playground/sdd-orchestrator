"use client";

import { useSearchParams } from "next/navigation";
import { useYouTubeTab } from "../../hooks/useYouTubeTab";
import type { YouTubeCredential } from "../../types";

type Props = { projectId: number | null };

export default function YouTubeTab({ projectId }: Props) {
  const searchParams = useSearchParams();
  const oauthCode = searchParams.get("code");
  const oauthState = searchParams.get("state");

  const { credential, isLoading, isConnecting, handleConnect, handleDisconnect } = useYouTubeTab({
    projectId,
    oauthCode,
    oauthState,
  });

  if (!projectId) {
    return (
      <div className="grid gap-6">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">YouTube</h2>
          <p className="text-xs text-zinc-500">
            Select a project first to manage YouTube connection.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-6">
      <div>
        <h2 className="text-lg font-semibold text-zinc-900">YouTube</h2>
        <p className="text-xs text-zinc-500">
          Connect a YouTube channel to this project for uploading Shorts.
        </p>
      </div>

      {/* Connection Status */}
      <div className="rounded-2xl border border-zinc-200 bg-white p-6">
        <h3 className="mb-4 text-xs font-semibold tracking-widest text-zinc-400 uppercase">
          Connection
        </h3>

        {isLoading || isConnecting ? (
          <div className="flex items-center gap-2 text-sm text-zinc-500">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-600" />
            {isConnecting ? "Connecting..." : "Loading..."}
          </div>
        ) : credential ? (
          <ConnectedChannelCard credential={credential} onDisconnect={handleDisconnect} />
        ) : (
          <div className="grid gap-3">
            <p className="text-sm text-zinc-500">No YouTube channel connected to this project.</p>
            <button
              onClick={handleConnect}
              className="flex w-fit items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-xs font-medium text-white transition hover:bg-red-700"
            >
              <YouTubeIcon className="h-4 w-4" />
              Connect YouTube
            </button>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="rounded-2xl border border-zinc-100 bg-zinc-50/50 p-4">
        <p className="text-[13px] leading-relaxed text-zinc-400">
          YouTube connection is per-project. Each project can connect to a different channel.
          Credentials are encrypted and stored securely. Uploads default to &ldquo;Private&rdquo;
          visibility.
        </p>
      </div>
    </div>
  );
}

// ── Connected channel detail card ──────────────────────────────

function ConnectedChannelCard({
  credential,
  onDisconnect,
}: {
  credential: YouTubeCredential;
  onDisconnect: () => void;
}) {
  const connectedDate = credential.created_at
    ? new Date(credential.created_at).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <div className="grid gap-4">
      <div className="flex items-start gap-3">
        {/* YouTube icon */}
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100">
          <YouTubeIcon className="h-5 w-5 text-red-600" />
        </div>

        {/* Channel info */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium text-zinc-900">
              {credential.channel_title || "Connected Channel"}
            </p>
            <span className="shrink-0 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[12px] font-semibold text-emerald-600">
              Connected
            </span>
          </div>

          {/* Detail rows */}
          <dl className="mt-2 grid gap-1 text-xs">
            {credential.channel_id && (
              <div className="flex gap-2">
                <dt className="shrink-0 text-zinc-400">Channel ID</dt>
                <dd className="truncate font-mono text-zinc-600">{credential.channel_id}</dd>
              </div>
            )}
            {connectedDate && (
              <div className="flex gap-2">
                <dt className="shrink-0 text-zinc-400">Connected</dt>
                <dd className="text-zinc-600">{connectedDate}</dd>
              </div>
            )}
          </dl>

          {/* YouTube channel link */}
          {credential.channel_id && (
            <a
              href={`https://www.youtube.com/channel/${credential.channel_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1 text-[13px] text-red-500 transition hover:text-red-600"
            >
              View on YouTube
              <svg
                className="h-3 w-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
            </a>
          )}
        </div>
      </div>

      <button
        onClick={onDisconnect}
        className="w-fit rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-500 transition hover:border-red-200 hover:text-red-500"
      >
        Disconnect
      </button>
    </div>
  );
}

// ── Shared YouTube SVG icon ─────────────────────────────────────

function YouTubeIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor">
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
    </svg>
  );
}
