"use client";

import { useState, useId, useRef, useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cx } from "./variants";

type TooltipProps = {
  content: string;
  children: ReactNode;
  position?: "top" | "bottom" | "left" | "right";
  className?: string; // for the tooltip content
  delay?: number;
};

export default function Tooltip({
  content,
  children,
  position = "top",
  className,
  delay = 300,
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const triggerRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const tooltipId = useId();

  useEffect(() => {
    if (isVisible && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      const scrollY = window.scrollY;
      const scrollX = window.scrollX;

      let top = 0;
      let left = 0;

      // Simple positioning logic
      switch (position) {
        case "top":
          top = rect.top + scrollY - 8;
          left = rect.left + scrollX + rect.width / 2;
          break;
        case "bottom":
          top = rect.bottom + scrollY + 8;
          left = rect.left + scrollX + rect.width / 2;
          break;
        case "left":
          top = rect.top + scrollY + rect.height / 2;
          left = rect.left + scrollX - 8;
          break;
        case "right":
          top = rect.top + scrollY + rect.height / 2;
          left = rect.right + scrollX + 8;
          break;
      }
      setCoords({ top, left });
    }
  }, [isVisible, position]);

  const handleMouseEnter = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);
    }, delay);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    // Small hide delay to prevent flicker when moving between trigger and tooltip edges
    timeoutRef.current = setTimeout(() => {
      setIsVisible(false);
    }, 100);
  };

  const handleFocus = () => {
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);
    }, delay);
  };

  const handleBlur = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsVisible(false);
  };

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <>
      <div
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={handleFocus}
        onBlur={handleBlur}
        aria-describedby={isVisible ? tooltipId : undefined}
        className="inline-flex" // Use inline-flex to minimize layout impact
      >
        {children}
      </div>
      {isVisible &&
        createPortal(
          <div
            id={tooltipId}
            role="tooltip"
            className={cx(
              "pointer-events-none fixed z-[var(--z-tooltip)] transform rounded-md bg-zinc-800 px-2.5 py-1.5 text-xs font-medium tracking-wide text-white shadow-lg",
              // Animation classes could be added here
              "animate-in fade-in zoom-in-95 transition-opacity duration-150",
              position === "top" && "-translate-x-1/2 -translate-y-full",
              position === "bottom" && "-translate-x-1/2",
              position === "left" && "-translate-x-full -translate-y-1/2",
              position === "right" && "-translate-y-1/2",
              className
            )}
            style={{ top: coords.top, left: coords.left }}
          >
            {content}
            {/* Arrow could be added here if desired */}
          </div>,
          document.body
        )}
    </>
  );
}
