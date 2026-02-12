"use client";

import Link from "next/link";
import { Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import {
  Settings,
  FlaskConical,
  Users,
  Mic,
  Music,
  Image,
  Clapperboard,
  ScrollText,
} from "lucide-react";
import { useUIStore } from "../../store/useUIStore";
import { cx } from "../ui/variants";
import CommandPalette from "../ui/CommandPalette";
import { ToastContainer } from "../ui/Toast";
import ConnectionGuard from "./ConnectionGuard";
import PersistentContextBar from "../context/PersistentContextBar";
import { useBackendHealth } from "../../hooks/useBackendHealth";
import type { ReactNode, ComponentType } from "react";

type NavItem = {
  href: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  exact?: boolean;
  matchTab?: string;
};

const NAV_GROUPS: (NavItem[] | "sep")[] = [
  [{ href: "/studio", label: "Studio", icon: Clapperboard }],
  "sep",
  [
    { href: "/scripts", label: "Scripts", icon: ScrollText },
    { href: "/characters", label: "Characters", icon: Users },
    { href: "/voices", label: "Voices", icon: Mic },
    { href: "/music", label: "Music", icon: Music },
    { href: "/backgrounds", label: "Backgrounds", icon: Image },
  ],
  "sep",
  [
    { href: "/lab", label: "Lab", icon: FlaskConical },
    { href: "/manage", label: "Manage", icon: Settings },
  ],
];

function isNavActive(item: NavItem, pathname: string, tab: string | null) {
  if (item.matchTab) return pathname === "/manage" && tab === item.matchTab;
  if (item.href === "/manage") return pathname.startsWith("/manage");
  if (item.exact) return pathname === item.href;
  return pathname.startsWith(item.href);
}

/** Extracted so it can be wrapped in Suspense (useSearchParams requirement) */
function NavBar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentTab = searchParams.get("tab");

  return (
    <nav className="flex items-center gap-1">
      {NAV_GROUPS.map((group, gi) =>
        group === "sep" ? (
          <div key={`sep-${gi}`} className="mx-1 h-4 w-px bg-zinc-200" />
        ) : (
          group.map((item) => {
            const Icon = item.icon;
            const active = isNavActive(item, pathname, currentTab);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cx(
                  "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition",
                  active
                    ? "bg-zinc-900 text-white"
                    : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700"
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
              </Link>
            );
          })
        )
      )}
    </nav>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const hasToasts = useUIStore((s) => s.toasts.length > 0);
  const connectionStatus = useBackendHealth();

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gradient-to-br from-zinc-50 via-white to-zinc-100 font-[family-name:var(--font-sans)]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[9999] focus:rounded-lg focus:bg-zinc-900 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white focus:shadow-lg"
      >
        Skip to main content
      </a>
      {/* Header */}
      <header className="flex h-[var(--nav-height)] shrink-0 items-center justify-between border-b border-zinc-200/60 bg-white/80 px-6 backdrop-blur-lg">
        <Suspense>
          <NavBar />
        </Suspense>
        <kbd className="hidden rounded border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 text-[12px] text-zinc-400 sm:inline-block">
          <span className="text-zinc-300">&#x2318;</span>K
        </kbd>
      </header>

      <PersistentContextBar />

      {/* Content */}
      <div id="main-content" tabIndex={-1} className="flex-1 overflow-y-auto outline-none">
        {children}
      </div>

      <CommandPalette />
      {hasToasts && <ToastContainer />}
      <ConnectionGuard status={connectionStatus} />
    </div>
  );
}
