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

/** App-wide max-width content container (SSOT). */
export const CONTAINER_CLASSES = "mx-auto w-full max-w-7xl px-6";

// ── Side-panel tokens ──────────────────────────────────────

/** Two-column grid: main content + 280px side panel. */
export const SIDE_PANEL_LAYOUT = "grid gap-6 md:grid-cols-[1fr_280px]";

/** Page-level 2-column grid: primary content + secondary panel (xl+). */
export const PAGE_2COL_LAYOUT = "grid gap-6 xl:grid-cols-[1fr_var(--secondary-panel-width)]";

/** Secondary panel container: hidden until xl, sticky top. */
export const SECONDARY_PANEL_CLASSES = "hidden xl:block sticky top-4 self-start space-y-4";

// ── Studio layout ───────────────────────────────────────────

/** 2-column grid: left scene list + center editor (Direct tab). */
export const STUDIO_2COL_LAYOUT =
  "grid grid-cols-[280px_1fr] gap-0 h-full min-h-[600px] overflow-hidden";

export const LEFT_PANEL_CLASSES =
  "flex flex-col border-r border-zinc-200 bg-zinc-50/50 overflow-y-auto";
export const CENTER_PANEL_CLASSES = "flex flex-col overflow-y-auto";

/** Publish tab: settings (left) + preview/output (right). */
export const PUBLISH_2COL_LAYOUT = "grid grid-cols-1 gap-6 md:grid-cols-[1fr_380px] md:items-start";

/** Sticky floating card for the right-side panel. */
export const SIDE_PANEL_CLASSES =
  "sticky top-4 self-start space-y-4 rounded-2xl border border-zinc-200 bg-white p-4";

/** Section label inside a side panel. */
export const SIDE_PANEL_LABEL =
  "mb-2 block text-[12px] font-medium tracking-wider text-zinc-400 uppercase";

/** Section header inside a form card (e.g., "Characters", "Agent Settings"). */
export const SECTION_HEADER_CLASSES =
  "text-xs font-semibold tracking-[0.2em] text-zinc-700 uppercase";

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

/** Form field label. */
export const FORM_LABEL_CLASSES = "text-sm font-medium text-zinc-700";

/** Compact form input (no border-radius-2xl, used in config editors). */
export const FORM_INPUT_COMPACT_CLASSES =
  "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400";

/** Compact form label (block, smaller tracking). */
export const FORM_LABEL_COMPACT_CLASSES = "block text-xs font-semibold text-zinc-500";

// ── Interactive state tokens ──────────────────────────────────

/** Tab/toggle active state (filled pill). */
export const TAB_ACTIVE = "bg-zinc-900 text-white";
/** Tab/toggle inactive state. */
export const TAB_INACTIVE = "text-zinc-500 hover:text-zinc-700 hover:bg-zinc-100";

/** Filter pill active state (rounded-full context). */
export const FILTER_PILL_ACTIVE = "bg-zinc-900 text-white";
/** Filter pill inactive state. */
export const FILTER_PILL_INACTIVE = "bg-zinc-100 text-zinc-500 hover:bg-zinc-200";

/** Sidebar nav item active state. */
export const SIDEBAR_ACTIVE =
  "border-l-2 border-zinc-900 bg-zinc-100 pl-2 font-medium text-zinc-900";
/** Sidebar nav item inactive state. */
export const SIDEBAR_INACTIVE = "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700";

// ── Semantic color tokens ────────────────────────────────────

/** Success state colors (standardized to emerald). */
export const SUCCESS_BG = "bg-emerald-50";
export const SUCCESS_TEXT = "text-emerald-700";
export const SUCCESS_BORDER = "border-emerald-200";
export const SUCCESS_BUTTON = "bg-emerald-600 hover:bg-emerald-500";
export const SUCCESS_ICON = "text-emerald-500";

/** Error state colors (standardized to red). */
export const ERROR_BG = "bg-red-50";
export const ERROR_TEXT = "text-red-700";
export const ERROR_BORDER = "border-red-200";
export const ERROR_BUTTON = "bg-red-600 hover:bg-red-700";
export const ERROR_ICON = "text-red-500";
export const ERROR_INPUT_BORDER = "border-red-500";
export const ERROR_INPUT_FOCUS = "focus:border-red-500 focus:ring-red-500";

/** Warning state colors. */
export const WARNING_BG = "bg-amber-50";
export const WARNING_TEXT = "text-amber-700";
export const WARNING_BORDER = "border-amber-200";
export const WARNING_BUTTON = "bg-amber-600 hover:bg-amber-700";
export const WARNING_ICON = "text-amber-500";

/** Info state colors. */
export const INFO_BG = "bg-indigo-50";
export const INFO_TEXT = "text-indigo-700";
export const INFO_BORDER = "border-indigo-200";
export const INFO_BUTTON = "bg-indigo-600 hover:bg-indigo-700";
export const INFO_ICON = "text-indigo-500";
