"use client";

import type { ConnectionStatus } from "../../hooks/useBackendHealth";

type Props = {
  connectionStatus: ConnectionStatus;
};

export default function AppFooter({ connectionStatus }: Props) {
  const isConnected = connectionStatus === "connected";

  return (
    <footer className="flex h-7 shrink-0 items-center justify-between border-t border-zinc-200/60 bg-white/60 px-5 text-[11px] text-zinc-400 backdrop-blur-sm">
      {/* Left: connection status */}
      <div className="flex items-center gap-1.5">
        <span
          aria-hidden="true"
          className={`h-1.5 w-1.5 rounded-full ${isConnected ? "bg-emerald-500" : "bg-red-400"}`}
        />
        <span>{isConnected ? "연결됨" : "연결 끊김"}</span>
      </div>

      {/* Center: branding */}
      <span className="font-medium tracking-wide text-zinc-300">Shorts Producer</span>

      {/* Right: shortcut hint */}
      <kbd className="rounded border border-zinc-200 bg-zinc-50 px-1 py-px text-[11px] text-zinc-400">
        <span className="text-zinc-300">&#x2318;</span>K
      </kbd>
    </footer>
  );
}
