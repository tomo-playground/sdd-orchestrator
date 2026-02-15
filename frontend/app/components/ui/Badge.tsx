"use client";

import type { ReactNode } from "react";
import {
  cx,
  SUCCESS_BG, SUCCESS_TEXT,
  WARNING_BG, WARNING_TEXT,
  ERROR_BG, ERROR_TEXT,
  INFO_BG, INFO_TEXT
} from "./variants";

// ── Types ────────────────────────────────────────────────────
export type BadgeVariant = "success" | "warning" | "error" | "info" | "default" | "secondary" | "outline" | "destructive";
export type BadgeSize = "sm" | "md";

export type BadgeProps = {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
};

// ── Variant / size maps ──────────────────────────────────────
const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-zinc-900 text-white hover:bg-zinc-800",
  secondary: "bg-zinc-100 text-zinc-900 hover:bg-zinc-200",
  outline: "text-zinc-900 border border-zinc-200 hover:bg-zinc-100",
  destructive: "bg-rose-500 text-white hover:bg-rose-600",
  success: `${SUCCESS_BG} ${SUCCESS_TEXT}`,
  warning: `${WARNING_BG} ${WARNING_TEXT}`,
  error: `${ERROR_BG} ${ERROR_TEXT}`,
  info: `${INFO_BG} ${INFO_TEXT}`,
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "text-[12px] px-1.5 py-0.5",
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
