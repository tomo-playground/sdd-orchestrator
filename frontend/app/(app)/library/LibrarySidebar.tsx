"use client";

import { useCallback, useEffect, useState } from "react";
import { Users, Mic, Music, Image, ChevronLeft, ChevronRight, type LucideIcon } from "lucide-react";
import { cx, SIDEBAR_ACTIVE, SIDEBAR_INACTIVE } from "../../components/ui/variants";

export type LibraryTab = "characters" | "voices" | "music" | "backgrounds";

type NavItem = { id: LibraryTab; label: string; icon: LucideIcon };

const NAV_ITEMS: NavItem[] = [
  { id: "characters", label: "Characters", icon: Users },
  { id: "voices", label: "Voices", icon: Mic },
  { id: "music", label: "Music", icon: Music },
  { id: "backgrounds", label: "Backgrounds", icon: Image },
];

const STORAGE_KEY = "librarySidebarCollapsed";

export default function LibrarySidebar({
  activeTab,
  onTabChange,
}: {
  activeTab: LibraryTab;
  onTabChange: (tab: LibraryTab) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setCollapsed(localStorage.getItem(STORAGE_KEY) === "true"); // eslint-disable-line react-hooks/set-state-in-effect
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
      <nav className="flex-1 overflow-y-auto py-3">
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
                    active ? SIDEBAR_ACTIVE : SIDEBAR_INACTIVE,
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
