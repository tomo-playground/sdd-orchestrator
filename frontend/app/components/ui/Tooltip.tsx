"use client";

import { useState, useRef, useEffect, type ReactNode } from "react";
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
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);
    }, delay);
  };

  const handleMouseLeave = () => {
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
        className="inline-flex" // Use inline-flex to minimize layout impact
      >
        {children}
      </div>
      {isVisible &&
        createPortal(
          <div
            className={cx(
              "fixed z-[var(--z-tooltip)] px-2.5 py-1.5 text-xs font-medium text-white bg-zinc-800 rounded-md shadow-lg pointer-events-none transform tracking-wide",
              // Animation classes could be added here
              "transition-opacity duration-150 animate-in fade-in zoom-in-95",
              position === "top" && "-translate-x-1/2 -translate-y-full",
              position === "bottom" && "-translate-x-1/2",
              position === "left" && "-translate-y-1/2 -translate-x-full",
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
