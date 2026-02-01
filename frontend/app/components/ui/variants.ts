/**
 * Common UI design tokens and helpers.
 * Shared across Button, Badge, Modal, ConfirmDialog, etc.
 */

// ── cx helper ────────────────────────────────────────────────
/** Merge class strings, filtering out falsy values. */
export function cx(
  ...classes: (string | false | null | undefined | 0)[]
): string {
  return classes.filter(Boolean).join(" ");
}

// ── Shared design tokens ─────────────────────────────────────

/** Overlay backdrop used by Modal / ConfirmDialog. */
export const OVERLAY_CLASSES =
  "fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/80 backdrop-blur-md";

/** Standard card surface (used inside modals, panels, etc.). */
export const CARD_CLASSES =
  "rounded-2xl bg-white shadow-xl border border-zinc-200";

/** Small uppercase label used in section headers. */
export const LABEL_CLASSES =
  "text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-400";

// ── Size / Variant maps ──────────────────────────────────────

/** Reusable focus-visible ring. */
export const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-zinc-400";

/** Disabled state applied to interactive elements. */
export const DISABLED_CLASSES = "disabled:opacity-50 disabled:cursor-not-allowed";
