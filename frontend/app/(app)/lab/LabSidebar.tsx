"use client";

import { useCallback, useEffect, useState } from "react";
import { Tag, Image, BarChart3, ChevronLeft, ChevronRight, type LucideIcon } from "lucide-react";
import { cx, SIDEBAR_ACTIVE, SIDEBAR_INACTIVE } from "../../components/ui/variants";

// ── Types ────────────────────────────────────────────────────

export type LabTab = "tag-lab" | "scene-lab" | "analytics";

type NavItem = {
  id: LabTab;
  label: string;
  icon: LucideIcon;
  description: string;
};

// ── Navigation structure ─────────────────────────────────────

const NAV_ITEMS: NavItem[] = [
  {
    id: "tag-lab",
    label: "Tag Lab",
    icon: Tag,
    description: "Tag rendering accuracy",
  },
  {
    id: "scene-lab",
    label: "Scene Lab",
    icon: Image,
    description: "Scene translation validation",
  },
  {
    id: "analytics",
    label: "Analytics",
    icon: BarChart3,
    description: "Quality metrics dashboard",
  },
];

const STORAGE_KEY = "labSidebarCollapsed";

// ── Component ────────────────────────────────────────────────

export default function LabSidebar({
  activeTab,
  onTabChange,
}: {
  activeTab: LabTab;
  onTabChange: (tab: LabTab) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- SSR-safe: read localStorage after hydration
    setCollapsed(localStorage.getItem(STORAGE_KEY) === "true");
  }, []);

  const toggleCollapse = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  const sidebarWidth = collapsed
    ? "w-[var(--sidebar-collapsed-width)]"
    : "w-[var(--sidebar-width)]";

  return (
    <aside
      className={cx(
        "hidden flex-col border-r border-zinc-200 bg-white transition-[width] duration-200 lg:flex",
        sidebarWidth
      )}
    >
      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-0.5 px-1.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <li key={item.id}>
                <button
                  onClick={() => onTabChange(item.id)}
                  title={collapsed ? item.label : undefined}
                  className={cx(
                    "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs transition",
                    active ? SIDEBAR_ACTIVE : SIDEBAR_INACTIVE,
                    collapsed && "justify-center px-0"
                  )}
                >
                  <Icon className="h-3.5 w-3.5 shrink-0" />
                  {!collapsed && (
                    <div className="min-w-0">
                      <div className="truncate">{item.label}</div>
                      <div className="truncate text-[12px] text-zinc-400">{item.description}</div>
                    </div>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
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
