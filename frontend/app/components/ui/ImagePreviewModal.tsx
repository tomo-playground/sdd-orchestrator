"use client";

import { useEffect, useState } from "react";

type ImagePreviewModalProps = {
  src: string | null;
  candidates?: string[];
  onClose: () => void;
};

export default function ImagePreviewModal({ src, candidates, onClose }: ImagePreviewModalProps) {
  const [currentSrc, setCurrentSrc] = useState<string | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Initialize state when src or candidates change
  useEffect(() => {
    if (src) {
      setCurrentSrc(src);
      if (candidates && candidates.length > 0) {
        const idx = candidates.indexOf(src);
        setCurrentIndex(idx >= 0 ? idx : 0);
      }
    }
  }, [src, candidates]);

  const handleNext = () => {
    if (!candidates || candidates.length === 0) return;
    const nextIndex = (currentIndex + 1) % candidates.length;
    setCurrentIndex(nextIndex);
    setCurrentSrc(candidates[nextIndex]);
  };

  const handlePrev = () => {
    if (!candidates || candidates.length === 0) return;
    const prevIndex = (currentIndex - 1 + candidates.length) % candidates.length;
    setCurrentIndex(prevIndex);
    setCurrentSrc(candidates[prevIndex]);
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") handlePrev();
      if (e.key === "ArrowRight") handleNext();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, currentIndex, candidates]); // Re-bind when index changes to capture correct state

  if (!currentSrc) return null;

  const showNavigation = candidates && candidates.length > 1;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 p-4"
      onClick={onClose}
    >
      <div className="relative flex max-h-[90vh] max-w-[90vw] items-center justify-center">
        {/* Previous Button */}
        {showNavigation && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              handlePrev();
            }}
            className="absolute -left-16 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white/50 backdrop-blur-sm transition hover:bg-white/20 hover:text-white"
            aria-label="Previous image"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-8 w-8">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        )}

        <img
          src={currentSrc}
          alt={`Preview ${showNavigation ? `${currentIndex + 1}/${candidates?.length}` : ""}`}
          className="max-h-[85vh] max-w-[85vw] object-contain shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        />

        {/* Next Button */}
        {showNavigation && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleNext();
            }}
            className="absolute -right-16 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white/50 backdrop-blur-sm transition hover:bg-white/20 hover:text-white"
            aria-label="Next image"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-8 w-8">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}

        {/* Indicator */}
        {showNavigation && (
          <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 flex gap-2">
            {candidates?.map((_, idx) => (
              <div
                key={idx}
                className={`h-2 w-2 rounded-full transition-all ${idx === currentIndex ? "bg-white w-4" : "bg-white/30 hover:bg-white/50"
                  }`}
              />
            ))}
          </div>
        )}

        {/* Close Button - Fixed to screen top-right */}
        <button
          onClick={onClose}
          className="fixed top-6 right-6 z-[110] flex h-12 w-12 items-center justify-center rounded-full bg-black/50 text-white backdrop-blur-sm transition hover:bg-black/70"
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
