"use client";

import { type ButtonHTMLAttributes, type ReactNode, forwardRef } from "react";
import {
  cx,
  FOCUS_RING,
  DISABLED_CLASSES,
  ERROR_BUTTON,
  SUCCESS_BUTTON,
  WARNING_BUTTON,
} from "./variants";
import LoadingSpinner from "./LoadingSpinner";

// ── Types ────────────────────────────────────────────────────
export type ButtonVariant =
  | "primary"
  | "secondary"
  | "danger"
  | "ghost"
  | "gradient"
  | "success"
  | "warning"
  | "outline";

export type ButtonSize = "sm" | "md" | "lg";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: boolean;
  loading?: boolean;
  children: ReactNode;
};

// ── Variant / size maps ──────────────────────────────────────
const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-zinc-900 text-white hover:bg-zinc-800 shadow-sm",
  secondary: "bg-zinc-100 text-zinc-700 hover:bg-zinc-200 border border-zinc-200",
  danger: `${ERROR_BUTTON} text-white shadow-sm`,
  ghost: "bg-transparent text-zinc-600 hover:bg-zinc-100",
  gradient:
    "bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600 shadow-sm",
  success: `${SUCCESS_BUTTON} text-white shadow-sm`,
  warning: `${WARNING_BUTTON} text-white shadow-sm`,
  outline:
    "border border-zinc-300 bg-white text-zinc-600 hover:bg-zinc-50 hover:border-zinc-400 shadow-sm",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "text-xs px-3 py-1.5 gap-1",
  md: "text-sm px-4 py-2 gap-1.5",
  lg: "text-sm px-6 py-3 gap-2",
};

const iconSizeClasses: Record<ButtonSize, string> = {
  sm: "text-xs p-1.5",
  md: "text-sm p-2",
  lg: "text-sm p-3",
};

const spinnerSize: Record<ButtonSize, "sm" | "md"> = {
  sm: "sm",
  md: "sm",
  lg: "md",
};

// ── Component ────────────────────────────────────────────────
const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      icon = false,
      loading = false,
      disabled,
      children,
      className,
      ...rest
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cx(
          "inline-flex items-center justify-center rounded-full font-semibold transition-colors",
          variantClasses[variant],
          icon ? iconSizeClasses[size] : sizeClasses[size],
          FOCUS_RING,
          DISABLED_CLASSES,
          className
        )}
        {...rest}
      >
        {loading ? (
          <>
            <LoadingSpinner size={spinnerSize[size]} color="text-current" className="shrink-0" />
            <span>{children}</span>
          </>
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;
