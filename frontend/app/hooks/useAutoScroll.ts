"use client";

import { useRef, useEffect, useCallback } from "react";

/**
 * Auto-scroll to bottom when new content is added,
 * unless the user has scrolled up manually.
 */
export function useAutoScroll<T>(deps: T[]) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const threshold = 80;
    isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  }, []);

  const depsLength = deps.length;

  useEffect(() => {
    if (!isAtBottomRef.current) return;
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [depsLength]);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
      isAtBottomRef.current = true;
    }
  }, []);

  return { containerRef, handleScroll, scrollToBottom };
}
