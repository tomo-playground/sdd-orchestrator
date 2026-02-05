"use client";

import { useEffect, useRef, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";
import { CARD_CLASSES, cx } from "./variants";

type PopoverProps = {
  anchorRef: RefObject<HTMLElement | null>;
  open: boolean;
  onClose: () => void;
  align?: "left" | "right";
  className?: string;
  children: ReactNode;
};

export default function Popover({
  anchorRef,
  open,
  onClose,
  align = "left",
  className,
  children,
}: PopoverProps) {
  const popRef = useRef<HTMLDivElement>(null);

  // Click-outside
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      const target = e.target as Node;
      if (
        popRef.current &&
        !popRef.current.contains(target) &&
        anchorRef.current &&
        !anchorRef.current.contains(target)
      ) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open, onClose, anchorRef]);

  // ESC key
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  /* eslint-disable react-hooks/refs -- Popover intentionally reads anchorRef position during render */
  if (!open || !anchorRef.current) return null;

  const rect = anchorRef.current.getBoundingClientRect();
  /* eslint-enable react-hooks/refs */
  const style: React.CSSProperties = {
    position: "fixed",
    top: rect.bottom + 4,
    zIndex: "var(--z-popover)",
    ...(align === "left" ? { left: rect.left } : { right: window.innerWidth - rect.right }),
  };

  return createPortal(
    <div
      ref={popRef}
      style={style}
      className={cx(CARD_CLASSES, "min-w-[200px] py-1 shadow-lg", className)}
    >
      {children}
    </div>,
    document.body
  );
}
