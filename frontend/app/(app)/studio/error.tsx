"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function StudioError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[Studio Error]", error);
  }, [error]);

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-6 p-8">
      <div className="flex flex-col items-center gap-2">
        <h2 className="text-xl font-semibold text-red-400">Studio를 불러올 수 없습니다</h2>
        <p className="max-w-md text-center text-sm text-zinc-400">
          {error.message || "스토리보드를 로드하는 중 문제가 발생했습니다."}
        </p>
      </div>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="rounded bg-zinc-700 px-4 py-2 text-sm text-white hover:bg-zinc-600"
        >
          다시 시도
        </button>
        <Link
          href="/"
          className="rounded bg-zinc-800 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
        >
          스토리보드 목록으로
        </Link>
        <button
          onClick={() => window.location.reload()}
          className="rounded bg-zinc-800 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
        >
          새로고침
        </button>
      </div>
    </div>
  );
}
