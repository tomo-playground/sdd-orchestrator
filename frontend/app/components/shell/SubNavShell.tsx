"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cx, TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";

// ── Types ────────────────────────────────────────────────────

export type SubNavTab = {
  href: string;
  label: string;
  icon: LucideIcon;
};

type SubNavShellProps = {
  tabs: SubNavTab[];
  footerLink?: SubNavTab;
  children: ReactNode;
};

// ── NavTab ───────────────────────────────────────────────────

function NavTab({ tab, pathname, className }: { tab: SubNavTab; pathname: string; className?: string }) {
  const Icon = tab.icon;
  const active = pathname.startsWith(tab.href);
  return (
    <Link
      href={tab.href}
      className={cx(
        "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition",
        active ? TAB_ACTIVE : TAB_INACTIVE,
        className
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {tab.label}
    </Link>
  );
}

// ── SubNavShell ──────────────────────────────────────────────

export default function SubNavShell({ tabs, footerLink, children }: SubNavShellProps) {
  const pathname = usePathname();

  return (
    <div className="flex flex-col gap-0">
      {/* Tab bar */}
      <div className="border-b border-zinc-100 bg-white/90 px-8 py-3 backdrop-blur-md">
        <nav className="flex items-center gap-1">
          {tabs.map((tab) => (
            <NavTab key={tab.href} tab={tab} pathname={pathname} />
          ))}

          {footerLink && (
            <NavTab tab={footerLink} pathname={pathname} className="ml-auto" />
          )}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">{children}</div>
    </div>
  );
}
