"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ArrowLeft,
  Users,
  Palette,
  Mic,
  Music,
  Settings,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  type LucideIcon,
} from "lucide-react";
import { useCallback, useState } from "react";

import { cx, LABEL_CLASSES, SIDEBAR_ACTIVE, SIDEBAR_INACTIVE } from "../ui/variants";

// ── Types ────────────────────────────────────────────────────

type NavItem = {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string;
};

type NavGroup = {
  key: string;
  label: string;
  items: NavItem[];
};

// ── Navigation structure ─────────────────────────────────────

export const NAV_GROUPS: NavGroup[] = [
  {
    key: "assets",
    label: "Assets",
    items: [
      { id: "characters", label: "Characters", icon: Users, href: "/admin/characters" },
      { id: "styles", label: "Styles", icon: Palette, href: "/admin/styles" },
      { id: "voices", label: "Voices", icon: Mic, href: "/admin/voices" },
      { id: "music", label: "Music", icon: Music, href: "/admin/music" },
    ],
  },
  {
    key: "tools",
    label: "Tools",
    items: [
      { id: "system", label: "System", icon: Settings, href: "/admin/system" },
    ],
  },
];

const STORAGE_KEY = "adminSidebarCollapsed";
const GROUPS_STORAGE_KEY = "adminSidebarCollapsedGroups";

// ── Sidebar ──────────────────────────────────────────────────

export default function AdminSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(() =>
    typeof window !== "undefined" && localStorage.getItem(STORAGE_KEY) === "true",
  );
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(() => {
    if (typeof window === "undefined") return new Set();
    const saved = localStorage.getItem(GROUPS_STORAGE_KEY);
    if (!saved) return new Set();
    try {
      return new Set(JSON.parse(saved));
    } catch {
      return new Set();
    }
  });

  const toggleCollapse = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  const toggleGroup = useCallback((key: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      localStorage.setItem(GROUPS_STORAGE_KEY, JSON.stringify([...next]));
      return next;
    });
  }, []);

  const sidebarWidth = collapsed
    ? "w-[var(--sidebar-collapsed-width)]"
    : "w-[var(--sidebar-width)]";

  const isActive = (href: string) => pathname.startsWith(href);

  return (
    <aside
      className={cx(
        "hidden flex-col border-r border-zinc-200 bg-white transition-[width] duration-200 lg:flex",
        sidebarWidth,
      )}
    >
      {/* Back link */}
      {!collapsed && (
        <div className="border-b border-zinc-100 px-5 py-3">
          <Link
            href="/studio"
            className="flex items-center gap-1.5 text-xs font-medium text-zinc-400 transition hover:text-zinc-600"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Studio
          </Link>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 pr-3 pl-5">
        {NAV_GROUPS.map((group) => {
          const isGroupCollapsed = collapsedGroups.has(group.key);
          return (
            <div key={group.key} className="mb-1">
              {!collapsed && (
                <button
                  onClick={() => toggleGroup(group.key)}
                  className={cx(
                    LABEL_CLASSES,
                    "flex w-full items-center gap-1 pt-4 pr-3 pb-1 pl-5 transition hover:text-zinc-600",
                  )}
                >
                  <ChevronDown
                    className={cx("h-3 w-3 transition-transform", isGroupCollapsed && "-rotate-90")}
                  />
                  {group.label}
                </button>
              )}
              {(!isGroupCollapsed || collapsed) && (
                <ul className="space-y-0.5">
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    const active = isActive(item.href);
                    return (
                      <li key={item.id}>
                        <Link
                          href={item.href}
                          title={collapsed ? item.label : undefined}
                          className={cx(
                            "flex w-full items-center gap-2.5 rounded-lg px-3 py-1.5 text-xs transition",
                            active ? SIDEBAR_ACTIVE : SIDEBAR_INACTIVE,
                            collapsed && "justify-center px-0",
                          )}
                        >
                          <Icon className="h-3.5 w-3.5 shrink-0" />
                          {!collapsed && <span className="truncate">{item.label}</span>}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={toggleCollapse}
        className="flex items-center justify-center border-t border-zinc-100 py-2 text-zinc-400 transition hover:text-zinc-600"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>
    </aside>
  );
}
