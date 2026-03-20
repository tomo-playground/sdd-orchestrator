"use client";

import { useState, useEffect } from "react";
import type { ConnectionStatus } from "../../hooks/useBackendHealth";

const STATUS_MESSAGES: Record<Exclude<ConnectionStatus, "connected">, string> = {
  disconnected: "Backend 서버와 연결이 끊어졌습니다. 재연결을 시도합니다...",
};

type CachedPreview = { name: string; url: string };

function getRandomPreview(): CachedPreview | null {
  try {
    const raw = localStorage.getItem("character_previews");
    if (!raw) return null;
    const previews: CachedPreview[] = JSON.parse(raw);
    if (!previews.length) return null;
    return previews[Math.floor(Math.random() * previews.length)];
  } catch {
    return null;
  }
}

export default function ConnectionGuard({ status }: { status: ConnectionStatus }) {
  const [preview, setPreview] = useState<CachedPreview | null>(null);
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    if (status !== "connected") {
      setPreview(getRandomPreview());
      setImgError(false);
    }
  }, [status]);

  if (status === "connected") return null;

  const message = STATUS_MESSAGES[status] ?? "Backend 연결 대기 중...";
  const showCharacter = preview && !imgError;

  return (
    <div
      className="fixed inset-0 z-[3000] flex flex-col items-center justify-center bg-zinc-950"
      role="alert"
    >
      <div aria-live="polite" className="sr-only">
        {message}
      </div>

      {showCharacter && (
        <div className="flex flex-col items-center">
          <div className="h-72 w-56 overflow-hidden rounded-2xl border border-white/10 shadow-2xl">
            <img
              src={preview.url}
              alt={preview.name}
              onError={() => setImgError(true)}
              className="h-full w-full object-cover object-top"
            />
          </div>
          <p className="mt-3 text-xs text-white/50">{preview.name}</p>
        </div>
      )}

      <div className="mt-6 flex flex-col items-center gap-2">
        <p className="text-sm font-medium text-white/80">Backend 연결 대기 중</p>
        <div className="flex items-center gap-2 text-xs text-white/40">
          <span
            className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400"
            aria-hidden="true"
          />
          {message}
        </div>
      </div>
    </div>
  );
}
