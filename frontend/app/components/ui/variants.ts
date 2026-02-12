/**
 * Common UI design tokens and helpers.
 * Shared across Button, Badge, Modal, ConfirmDialog, etc.
 */

// ── cx helper ────────────────────────────────────────────────
/** Merge class strings, filtering out falsy values. */
export function cx(...classes: (string | false | null | undefined | 0)[]): string {
  return classes.filter(Boolean).join(" ");
}

// ── Shared design tokens ─────────────────────────────────────

/** Overlay backdrop used by Modal / ConfirmDialog. */
export const OVERLAY_CLASSES =
  "fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/80 backdrop-blur-md";

/** Standard card surface (used inside modals, panels, etc.). */
export const CARD_CLASSES = "rounded-2xl bg-white shadow-xl border border-zinc-200";

/** Small uppercase label used in section headers. */
export const LABEL_CLASSES = "text-[12px] font-semibold uppercase tracking-[0.2em] text-zinc-400";

/** Page-level h1 title for independent list pages. */
export const PAGE_TITLE_CLASSES = "text-lg font-bold text-zinc-900";

/** Search input used in list pages. Add w-full or max-w-sm at the call site. */
export const SEARCH_INPUT_CLASSES =
  "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400";

// ── Size / Variant maps ──────────────────────────────────────

/** Reusable focus-visible ring. */
export const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-zinc-400";

/** Disabled state applied to interactive elements. */
export const DISABLED_CLASSES = "disabled:opacity-50 disabled:cursor-not-allowed";

// ── Layout tokens ───────────────────────────────────────────

/** Top-level navigation bar. */
export const NAV_CLASSES =
  "sticky top-0 z-[var(--z-nav)] border-b border-zinc-200/60 bg-white/80 backdrop-blur-lg";

/** Page-level sub-navigation (sticky at top of scroll area). */
export const SUB_NAV_CLASSES =
  "sticky top-0 z-[var(--z-sub-nav)] border-b border-zinc-100 bg-white/90 backdrop-blur-md";

/** Max-width content container, left-aligned within sidebar layout. */
export const CONTAINER_CLASSES = "w-full max-w-5xl px-6";

// ── Side-panel tokens ──────────────────────────────────────

/** Two-column grid: main content + 220px side panel. */
export const SIDE_PANEL_LAYOUT = "grid gap-6 md:grid-cols-[1fr_220px]";

/** Sticky floating card for the right-side panel. */
export const SIDE_PANEL_CLASSES =
  "sticky top-4 self-start space-y-4 rounded-2xl border border-zinc-200 bg-white p-4";

/** Section label inside a side panel. */
export const SIDE_PANEL_LABEL =
  "mb-2 block text-[12px] font-semibold tracking-wider text-zinc-500 uppercase";

// ── Content section tokens ─────────────────────────────────

/** Glassmorphism card for content sections within the left column. */
export const SECTION_CLASSES =
  "rounded-3xl border border-white/60 bg-white/70 p-6 shadow-xl shadow-slate-200/40 backdrop-blur";

// ── Form input tokens ────────────────────────────────────────

/** Form text input / number input / select. */
export const FORM_INPUT_CLASSES =
  "w-full rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400";

/** Form textarea with inner shadow. */
export const FORM_TEXTAREA_CLASSES =
  "w-full rounded-2xl border border-zinc-200 bg-white/80 p-4 text-sm shadow-inner outline-none focus:border-zinc-400";

/** Form field label (uppercase tracking). */
export const FORM_LABEL_CLASSES =
  "text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase";

/** Compact form input (no border-radius-2xl, used in config editors). */
export const FORM_INPUT_COMPACT_CLASSES =
  "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400";

/** Compact form label (block, smaller tracking). */
export const FORM_LABEL_COMPACT_CLASSES = "block text-xs font-semibold text-zinc-500";
