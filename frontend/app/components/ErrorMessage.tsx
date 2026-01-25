import React from "react";

type ErrorMessageProps = {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
};

export default function ErrorMessage({
  title = "Error",
  message,
  onRetry,
  className = "",
}: ErrorMessageProps) {
  return (
    <div
      className={`flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 ${className}`}
    >
      <svg
        className="mt-0.5 h-5 w-5 shrink-0 text-rose-500"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <div className="flex-1">
        <h4 className="font-semibold text-rose-800">{title}</h4>
        <p className="mt-1 text-rose-600 opacity-90">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-3 rounded-lg bg-rose-100 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-200"
          >
            Try Again
          </button>
        )}
      </div>
    </div>
  );
}
