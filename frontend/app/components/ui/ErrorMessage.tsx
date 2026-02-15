import { AlertTriangle, XCircle } from "lucide-react";
import React from "react";
import { ERROR_BG, ERROR_BORDER, ERROR_TEXT, ERROR_ICON } from "./variants";

type ErrorMessageProps = {
  title?: string;
  message: string;
  className?: string;
  onRetry?: () => void;
};

export default function ErrorMessage({
  title = "Error",
  message,
  onRetry,
  className = "",
}: ErrorMessageProps) {
  if (!message) return null;

  return (
    <div
      className={`flex items-start gap-3 rounded-2xl border ${ERROR_BORDER} ${ERROR_BG} p-4 text-sm ${ERROR_TEXT} ${className}`}
    >
      <XCircle className={`mt-0.5 h-5 w-5 shrink-0 ${ERROR_ICON}`} />
      <div className="flex-1">
        <h4 className={`font-semibold ${ERROR_TEXT}`}>{title}</h4>
        <p className={`mt-1 ${ERROR_TEXT} opacity-90`}>{message}</p>
        {(message.includes("Network") || onRetry) && (
          <div className="mt-2">
            <button
              onClick={onRetry || (() => window.location.reload())}
              className={`mt-3 rounded-lg bg-white/50 px-3 py-1.5 text-xs font-medium ${ERROR_TEXT} hover:bg-white/80`}
            >
              {onRetry ? "Try Again" : "Reload Page"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
