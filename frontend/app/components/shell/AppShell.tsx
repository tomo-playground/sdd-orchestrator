"use client";

import Link from "next/link";
import { Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import {
  Home,
  Settings,
  FlaskConical,
  Users,
  FileText,
  Mic,
  Music,
  Clapperboard,
} from "lucide-react";
import { useStudioStore } from "../../store/useStudioStore";
import { cx } from "../ui/variants";
import CommandPalette from "../ui/CommandPalette";
import Toast from "../ui/Toast";
import ConnectionGuard from "./ConnectionGuard";
import Sidebar from "./Sidebar";
import { useBackendHealth } from "../../hooks/useBackendHealth";
import type { ReactNode, ComponentType } from "react";

type NavItem = {
  href: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  exact?: boolean;
  matchTab?: string;
};

/** Tabs surfaced as top-level nav — excluded from generic Manage active state */
const PROMOTED_TABS = new Set(["music"]);

const NAV_GROUPS: (NavItem[] | "sep")[] = [
  [
    { href: "/", label: "Home", icon: Home, exact: true },
    { href: "/storyboards", label: "Stories", icon: FileText },
    { href: "/characters", label: "Characters", icon: Users },
    { href: "/voices", label: "Voices", icon: Mic },
    { href: "/manage?tab=music", label: "Music", icon: Music, matchTab: "music" },
  ],
  "sep",
  [{ href: "/studio", label: "Studio", icon: Clapperboard }],
  "sep",
  [
    { href: "/lab", label: "Lab", icon: FlaskConical },
    { href: "/manage", label: "Manage", icon: Settings },
  ],
];

function isNavActive(item: NavItem, pathname: string, tab: string | null) {
  if (item.matchTab) return pathname === "/manage" && tab === item.matchTab;
  if (item.href === "/manage")
    return pathname.startsWith("/manage") && !PROMOTED_TABS.has(tab ?? "");
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
  const pathname = usePathname();
  const showSidebar =
    !pathname.startsWith("/manage") &&
    !pathname.startsWith("/lab") &&
    !pathname.startsWith("/characters") &&
    !pathname.startsWith("/storyboards") &&
    !pathname.startsWith("/voices");
  const toast = useStudioStore((s) => s.toast);
  const connectionStatus = useBackendHealth();

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gradient-to-br from-zinc-50 via-white to-zinc-100 font-[family-name:var(--font-sans)]">
      {/* Header */}
      <header className="flex h-[var(--nav-height)] shrink-0 items-center justify-between border-b border-zinc-200/60 bg-white/80 px-6 backdrop-blur-lg">
        <Suspense>
          <NavBar />
        </Suspense>
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
      {toast && <Toast message={toast.message} type={toast.type} />}
      <ConnectionGuard status={connectionStatus} />
    </div>
  );
}
