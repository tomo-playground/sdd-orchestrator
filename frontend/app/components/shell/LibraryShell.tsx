"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Users, Palette, Mic, Music, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cx, TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";

// ── Types ────────────────────────────────────────────────────

type TabItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

const TABS: TabItem[] = [
  { href: "/library/characters", label: "Characters", icon: Users },
  { href: "/library/styles", label: "Styles", icon: Palette },
  { href: "/library/voices", label: "Voices", icon: Mic },
  { href: "/library/music", label: "Music", icon: Music },
];

// ── LibraryShell ─────────────────────────────────────────────

export default function LibraryShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex flex-col gap-0">
      {/* Tab bar */}
      <div className="border-b border-zinc-100 bg-white/90 px-8 py-3 backdrop-blur-md">
        <nav className="flex items-center gap-1">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = pathname.startsWith(tab.href);
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={cx(
                  "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition",
                  active ? TAB_ACTIVE : TAB_INACTIVE
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">{children}</div>
    </div>
  );
}
