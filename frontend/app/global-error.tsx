"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="bg-zinc-900 text-white">
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
          <h2 className="text-xl font-semibold text-red-400">
            Critical Error
          </h2>
          <p className="text-sm text-zinc-400">
            The application encountered a critical error.
          </p>
          <button
            onClick={reset}
            className="rounded bg-zinc-700 px-4 py-2 text-sm text-white hover:bg-zinc-600"
          >
            Reload
          </button>
        </div>
      </body>
    </html>
  );
}
