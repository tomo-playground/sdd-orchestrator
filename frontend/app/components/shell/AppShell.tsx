"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Clapperboard, Settings } from "lucide-react";
import { NAV_CLASSES, CONTAINER_CLASSES, cx } from "../ui/variants";
import CommandPalette from "../ui/CommandPalette";
import type { ReactNode } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: Home, exact: true },
  { href: "/studio", label: "Studio", icon: Clapperboard, exact: false },
  { href: "/manage", label: "Manage", icon: Settings, exact: false },
] as const;

function isActive(pathname: string, href: string, exact: boolean) {
  return exact ? pathname === href : pathname.startsWith(href);
}

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-zinc-50 via-white to-zinc-100 font-[family-name:var(--font-sans)]">
      <nav className={cx(NAV_CLASSES, "h-[var(--nav-height)]")}>
        <div className={cx(CONTAINER_CLASSES, "flex h-full items-center justify-between")}>
          {/* Left: logo + nav links */}
          <div className="flex items-center gap-5">
            <Link href="/" className="text-sm font-bold tracking-tight text-zinc-900">
              Shorts Producer
            </Link>
            <div className="flex items-center gap-1">
              {NAV_ITEMS.map(({ href, label, icon: Icon, exact }) => {
                const active = isActive(pathname, href, exact);
                return (
                  <Link
                    key={href}
                    href={href}
                    className={cx(
                      "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition",
                      active
                        ? "bg-zinc-900 text-white"
                        : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700"
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Right: Cmd+K hint */}
          <kbd className="hidden rounded border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 text-[10px] text-zinc-400 sm:inline-block">
            <span className="text-zinc-300">⌘</span>K
          </kbd>
        </div>
      </nav>

      {children}

      <CommandPalette />
    </div>
  );
}
