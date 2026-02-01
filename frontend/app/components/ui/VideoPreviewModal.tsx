"use client";

import { useEffect } from "react";

type VideoPreviewModalProps = {
  src: string | null;
  onClose: () => void;
};

export default function VideoPreviewModal({ src, onClose }: VideoPreviewModalProps) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  if (!src) return null;

  return (
    <div
      className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/90 p-4"
      onClick={onClose}
    >
      <div className="relative max-h-[90vh] max-w-[90vw]">
        <video
          src={src}
          controls
          autoPlay
          className="max-h-[90vh] max-w-[90vw] object-contain"
          onClick={(e) => e.stopPropagation()}
        />
        <button
          onClick={onClose}
          className="fixed top-6 right-6 z-[var(--z-modal-close)] flex h-12 w-12 items-center justify-center rounded-full bg-black/50 text-white backdrop-blur-sm transition hover:bg-black/70"
          aria-label="Close preview"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            className="h-6 w-6"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
