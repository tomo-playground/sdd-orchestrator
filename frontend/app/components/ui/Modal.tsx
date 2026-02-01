"use client";

import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cx, OVERLAY_CLASSES, CARD_CLASSES } from "./variants";

// ── Types ────────────────────────────────────────────────────
export type ModalSize = "sm" | "md" | "lg" | "xl";

export type ModalProps = {
  open: boolean;
  onClose: () => void;
  size?: ModalSize;
  /** When true, overlay click does NOT close the modal. */
  persistent?: boolean;
  children: ReactNode;
  className?: string;
};

type ModalSubProps = {
  children: ReactNode;
  className?: string;
};

// ── Size map ─────────────────────────────────────────────────
const sizeClasses: Record<ModalSize, string> = {
  sm: "max-w-sm w-full",
  md: "max-w-md w-full",
  lg: "max-w-lg w-full",
  xl: "max-w-xl w-full",
};

// ── Sub-components ───────────────────────────────────────────
function Header({ children, className }: ModalSubProps) {
  return (
    <div
      className={cx(
        "flex items-center justify-between px-5 py-4 border-b border-zinc-100",
        className,
      )}
    >
      {children}
    </div>
  );
}

function Footer({ children, className }: ModalSubProps) {
  return (
    <div
      className={cx(
        "flex items-center justify-end gap-2 px-5 py-4 border-t border-zinc-100",
        className,
      )}
    >
      {children}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────
function ModalRoot({
  open,
  onClose,
  size = "md",
  persistent = false,
  children,
  className,
}: ModalProps) {
  // ESC key handler
  useEffect(() => {
    if (!open) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  // Prevent body scroll while open
  useEffect(() => {
    if (!open) return;

    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className={OVERLAY_CLASSES}
      onClick={persistent ? undefined : onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className={cx(
          CARD_CLASSES,
          sizeClasses[size],
          "mx-4 overflow-hidden",
          className,
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}

// ── Compound export ──────────────────────────────────────────
const Modal = Object.assign(ModalRoot, { Header, Footer });
export default Modal;
