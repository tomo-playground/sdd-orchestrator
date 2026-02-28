"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useUIStore } from "../../store/useUIStore";
import CommandPalette from "../ui/CommandPalette";
import { ToastContainer } from "../ui/Toast";
import ConnectionGuard from "./ConnectionGuard";
import AdminSidebar, { NAV_GROUPS } from "./AdminSidebar";
import { useBackendHealth } from "../../hooks/useBackendHealth";

// ── AdminShell ───────────────────────────────────────────────

export default function AdminShell({ children }: { children: ReactNode }) {
  const hasToasts = useUIStore((s) => s.toasts.length > 0);
  const connectionStatus = useBackendHealth();

  return (
    <div className="mx-auto flex h-screen max-w-[1440px] flex-col overflow-hidden bg-gradient-to-br from-zinc-50 via-white to-zinc-100 font-[family-name:var(--font-sans)]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[9999] focus:rounded-lg focus:bg-zinc-900 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white focus:shadow-lg"
      >
        Skip to main content
      </a>

      {/* Header */}
      <header className="flex h-[var(--nav-height)] shrink-0 items-center justify-between border-b border-zinc-200/60 bg-white/80 px-8 backdrop-blur-lg">
        <Suspense>
          <AdminNavBar />
        </Suspense>
      </header>

      {/* Content: sidebar + main */}
      <div className="flex flex-1 overflow-hidden">
        <AdminSidebar />
        <main id="main-content" tabIndex={-1} className="flex-1 overflow-y-auto outline-none">
          {children}
        </main>
      </div>

      <CommandPalette />
      {hasToasts && <ToastContainer />}
      <ConnectionGuard status={connectionStatus} />
    </div>
  );
}

// ── Top nav bar ──────────────────────────────────────────────

const ALL_NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items);

function AdminNavBar() {
  const pathname = usePathname();
  const section = ALL_NAV_ITEMS.find((item) => pathname.startsWith(item.href))?.label ?? "Admin";

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-semibold tracking-widest text-zinc-400 uppercase">Admin</span>
      <span className="text-zinc-300">/</span>
      <span className="text-sm font-medium text-zinc-700">{section}</span>
    </div>
  );
}
