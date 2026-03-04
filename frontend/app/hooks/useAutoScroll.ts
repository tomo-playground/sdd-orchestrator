"use client";

import { useRef, useEffect, useCallback } from "react";

/**
 * Auto-scroll to bottom when new content is added,
 * unless the user has scrolled up manually.
 *
 * @param length - Number of items (triggers scroll on change)
 * @param lastTimestamp - Optional timestamp of last item (detects upserts)
 */
export function useAutoScroll(length: number, lastTimestamp?: number) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const threshold = 80;
    isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  }, []);

  useEffect(() => {
    if (!isAtBottomRef.current) return;
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [length, lastTimestamp]);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
      isAtBottomRef.current = true;
    }
  }, []);

  return { containerRef, handleScroll, scrollToBottom };
}
