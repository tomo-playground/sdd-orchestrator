"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Settings } from "lucide-react";
import { cx } from "../ui/variants";
import CommandPalette from "../ui/CommandPalette";
import Sidebar from "./Sidebar";
import type { ReactNode } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: Home, exact: true },
  { href: "/manage", label: "Manage", icon: Settings, exact: false },
] as const;

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const showSidebar = !pathname.startsWith("/manage");

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gradient-to-br from-zinc-50 via-white to-zinc-100 font-[family-name:var(--font-sans)]">
      {/* Header */}
      <header className="flex h-[var(--nav-height)] shrink-0 items-center justify-between border-b border-zinc-200/60 bg-white/80 px-6 backdrop-blur-lg">
        <div className="flex items-center gap-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon, exact }) => {
            const active = exact ? pathname === href : pathname.startsWith(href);
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
        <kbd className="hidden rounded border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 text-[10px] text-zinc-400 sm:inline-block">
          <span className="text-zinc-300">&#x2318;</span>K
        </kbd>
      </header>

      {/* Sidebar + Content */}
      <div className="flex flex-1 overflow-hidden">
        {showSidebar && <Sidebar />}
        <div className="flex-1 overflow-y-auto">{children}</div>
      </div>

      <CommandPalette />
    </div>
  );
}
