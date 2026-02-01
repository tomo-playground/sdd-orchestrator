"use client";

import type { ReactNode } from "react";
import { cx } from "./variants";

// ── Types ────────────────────────────────────────────────────
export type BadgeVariant = "success" | "warning" | "error" | "info" | "default";
export type BadgeSize = "sm" | "md";

export type BadgeProps = {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
};

// ── Variant / size maps ──────────────────────────────────────
const variantClasses: Record<BadgeVariant, string> = {
  success: "bg-emerald-100 text-emerald-700",
  warning: "bg-amber-100 text-amber-700",
  error: "bg-rose-100 text-rose-700",
  info: "bg-blue-100 text-blue-700",
  default: "bg-zinc-100 text-zinc-600",
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "text-[10px] px-1.5 py-0.5",
  md: "text-xs px-2 py-0.5",
};

// ── Component ────────────────────────────────────────────────
export default function Badge({
  children,
  variant = "default",
  size = "sm",
  className,
}: BadgeProps) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full font-medium leading-none",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
    >
      {children}
    </span>
  );
}
