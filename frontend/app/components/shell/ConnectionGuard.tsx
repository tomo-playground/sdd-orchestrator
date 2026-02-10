"use client";

import type { ConnectionStatus } from "../../hooks/useBackendHealth";
import { API_BASE } from "../../constants";

const VIDEO_URL = `${API_BASE.replace(":8000", ":9000")}/shorts-producer/shared/video/connection_loading.mp4`;

export default function ConnectionGuard({ status }: { status: ConnectionStatus }) {
  if (status === "connected") return null;

  return (
    <div className="fixed inset-0 z-[3000] flex flex-col items-center justify-center bg-zinc-950">
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
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
          서버 응답을 기다리고 있습니다...
        </div>
      </div>
    </div>
  );
}
