"use client";

export default function GlobalError({
  error: _error, // eslint-disable-line @typescript-eslint/no-unused-vars
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="bg-zinc-900 text-white">
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
          <h2 className="text-xl font-semibold text-red-400">심각한 오류가 발생했습니다</h2>
          <p className="text-sm text-zinc-400">애플리케이션에서 심각한 오류가 발생했습니다.</p>
          <button
            onClick={reset}
            className="rounded bg-zinc-700 px-4 py-2 text-sm text-white hover:bg-zinc-600"
          >
            새로고침
          </button>
        </div>
      </body>
    </html>
  );
}
