"use client";

import { useCallback, useEffect, useState } from "react";
import { FlaskConical, BarChart3, ChevronLeft, ChevronRight, type LucideIcon } from "lucide-react";
import { cx } from "../../components/ui/variants";

// ── Types ────────────────────────────────────────────────────

export type QualityTab = "evaluation" | "insights";

type NavItem = {
  id: QualityTab;
  label: string;
  icon: LucideIcon;
};

// ── Navigation structure ─────────────────────────────────────

const NAV_ITEMS: NavItem[] = [
  { id: "evaluation", label: "Evaluation", icon: FlaskConical },
  { id: "insights", label: "Insights", icon: BarChart3 },
];

const STORAGE_KEY = "qualitySidebarCollapsed";

// ── Component ────────────────────────────────────────────────

export default function QualitySidebar({
  activeTab,
  onTabChange,
}: {
  activeTab: QualityTab;
  onTabChange: (tab: QualityTab) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setCollapsed(localStorage.getItem(STORAGE_KEY) === "true");
  }, []);

  const toggleCollapse = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  const sidebarWidth = collapsed ? "w-14" : "w-48";

  return (
    <aside
      className={cx(
        "hidden flex-col border-r border-zinc-200 bg-white transition-[width] duration-200 lg:flex",
        sidebarWidth
      )}
    >
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
                    "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-xs transition",
                    active
                      ? "border-l-2 border-zinc-900 bg-zinc-100 pl-2 font-medium text-zinc-900"
                      : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700",
                    collapsed && "justify-center px-0"
                  )}
                >
                  <Icon className="h-3.5 w-3.5 shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

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
