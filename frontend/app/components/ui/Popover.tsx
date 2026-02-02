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

  if (!open || !anchorRef.current) return null;

  const rect = anchorRef.current.getBoundingClientRect();
  const style: React.CSSProperties = {
    position: "fixed",
    top: rect.bottom + 4,
    zIndex: 50,
    ...(align === "left"
      ? { left: rect.left }
      : { right: window.innerWidth - rect.right }),
  };

  return createPortal(
    <div ref={popRef} style={style} className={cx(CARD_CLASSES, "py-1 shadow-lg min-w-[200px]", className)}>
      {children}
    </div>,
    document.body,
  );
}
