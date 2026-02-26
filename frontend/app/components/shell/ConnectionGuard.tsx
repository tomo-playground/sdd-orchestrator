"use client";

import type { ConnectionStatus } from "../../hooks/useBackendHealth";
import { API_BASE } from "../../constants";

const VIDEO_URL = `${API_BASE.replace(":8000", ":9000")}/shorts-producer/shared/video/connection_loading.mp4`;

const STATUS_MESSAGES: Record<Exclude<ConnectionStatus, "connected">, string> = {
  disconnected: "Backend 서버와 연결이 끊어졌습니다. 재연결을 시도합니다...",
};

export default function ConnectionGuard({ status }: { status: ConnectionStatus }) {
  if (status === "connected") return null;

  const message = STATUS_MESSAGES[status] ?? "Backend 연결 대기 중...";

  return (
    <div
      className="fixed inset-0 z-[3000] flex flex-col items-center justify-center bg-zinc-950"
      role="alert"
    >
      {/* Screen reader live region for connection status */}
      <div aria-live="polite" className="sr-only">
        {message}
      </div>

      <video
        src={VIDEO_URL}
        autoPlay
        loop
        muted
        playsInline
        className="h-80 w-auto rounded-2xl object-contain"
      />
      <div className="mt-6 flex flex-col items-center gap-2">
        <p className="text-sm font-medium text-white/80">Backend 연결 대기 중</p>
        <div className="flex items-center gap-2 text-xs text-white/40">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" aria-hidden="true" />
          {message}
        </div>
      </div>
    </div>
  );
}
