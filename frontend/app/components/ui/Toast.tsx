import React, { useEffect, useState } from "react";

type ToastType = "success" | "error" | "info" | "warning";

type ToastProps = {
  message: string;
  type: ToastType;
  onClose?: () => void;
  duration?: number;
};

export default function Toast({ message, type, onClose, duration = 3000 }: ToastProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(() => onClose?.(), 300); // Wait for fade out animation
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const styles = {
    success: "bg-emerald-500 text-white shadow-emerald-500/20",
    error: "bg-rose-500 text-white shadow-rose-500/20",
    info: "bg-zinc-800 text-white shadow-zinc-800/20",
    warning: "bg-amber-500 text-white shadow-amber-500/20",
  };

  const icons = {
    success: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
    error: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
    info: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    warning: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
  };

  return (
    <div
      className={`fixed bottom-6 left-1/2 z-[var(--z-toast)] flex -translate-x-1/2 items-center gap-3 rounded-full px-6 py-3 text-sm font-medium shadow-lg transition-all duration-300 ${styles[type]
        } ${isVisible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"}`}
    >
      {icons[type]}
      <span>{message}</span>
      {onClose && (
        <button
          onClick={() => {
            setIsVisible(false);
            setTimeout(() => onClose(), 300);
          }}
          className="ml-2 rounded-full p-1 opacity-70 hover:bg-white/20 hover:opacity-100"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}
