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
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-8">
      <h2 className="text-xl font-semibold text-red-400">
        Failed to load Studio
      </h2>
      <p className="text-sm text-zinc-400">
        {error.message || "Could not load the storyboard."}
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="rounded bg-zinc-700 px-4 py-2 text-sm text-white hover:bg-zinc-600"
        >
          Try again
        </button>
        <Link
          href="/"
          className="rounded bg-zinc-800 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-700"
        >
          Back to list
        </Link>
      </div>
    </div>
  );
}
