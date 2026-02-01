"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[App Error]", error);
  }, [error]);

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-8">
      <h2 className="text-xl font-semibold text-red-400">
        Something went wrong
      </h2>
      <p className="text-sm text-zinc-400">
        {error.message || "An unexpected error occurred."}
      </p>
      <button
        onClick={reset}
        className="rounded bg-zinc-700 px-4 py-2 text-sm text-white hover:bg-zinc-600"
      >
        Try again
      </button>
    </div>
  );
}
