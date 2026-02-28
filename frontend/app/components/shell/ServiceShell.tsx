"use client";

import Link from "next/link";
import { Suspense } from "react";
import { usePathname } from "next/navigation";
import { Home, Clapperboard, FolderOpen, Settings, Wrench } from "lucide-react";

import { useUIStore } from "../../store/useUIStore";
import { cx, TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";
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
};

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Home", icon: Home, exact: true },
  { href: "/studio", label: "Studio", icon: Clapperboard },
  { href: "/library", label: "Library", icon: FolderOpen },
  { href: "/settings", label: "Settings", icon: Settings },
];

const DEV_ITEM: NavItem = {
  href: "/dev",
  label: "Dev",
  icon: Wrench,
};

function isNavActive(item: NavItem, pathname: string) {
  if (item.href === "/studio") return pathname.startsWith("/studio");
  if (item.href === "/library") return pathname.startsWith("/library");
  if (item.href === "/settings") return pathname.startsWith("/settings");
  if (item.exact) return pathname === item.href;
  return pathname.startsWith(item.href);
}

function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-1">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const active = isNavActive(item, pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cx(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition",
              active ? TAB_ACTIVE : TAB_INACTIVE
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {item.label}
          </Link>
        );
      })}

      {/* Separator */}
      <div className="mx-1 h-4 w-px bg-zinc-200" />

      {/* Dev link */}
      <Link
        href={DEV_ITEM.href}
        className={cx(
          "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition",
          pathname.startsWith("/dev") ? TAB_ACTIVE : TAB_INACTIVE
        )}
      >
        <DEV_ITEM.icon className="h-3.5 w-3.5" />
        {DEV_ITEM.label}
      </Link>
    </nav>
  );
}

export default function ServiceShell({ children }: { children: ReactNode }) {
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
          <NavBar />
        </Suspense>
        <kbd className="hidden rounded border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 text-[12px] text-zinc-400 sm:inline-block">
          <span className="text-zinc-300">&#x2318;</span>K
        </kbd>
      </header>

      <PersistentContextBar />

      {/* Content */}
      <div
        id="main-content"
        tabIndex={-1}
        className="flex-1 overflow-x-hidden overflow-y-auto outline-none"
      >
        {children}
      </div>

      <CommandPalette />
      {hasToasts && <ToastContainer />}
      <ConnectionGuard status={connectionStatus} />
    </div>
  );
}
