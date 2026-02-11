"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Tag,
  Palette,
  FileText,
  SlidersHorizontal,
  Settings,
  Trash2,
  Upload,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Library,
  FolderCog,
  type LucideIcon,
} from "lucide-react";
import { cx, LABEL_CLASSES } from "../../components/ui/variants";
import { useStudioStore } from "../../store/useStudioStore";

// ── Types ────────────────────────────────────────────────────

export type ManageTab = "tags" | "style" | "prompts" | "presets" | "youtube" | "settings" | "trash";

type NavItem = {
  id: ManageTab;
  label: string;
  icon: LucideIcon;
};

type NavGroup = {
  key: string;
  label: string;
  icon?: LucideIcon;
  items: NavItem[];
};

// ── Navigation structure ─────────────────────────────────────

const NAV_GROUPS: NavGroup[] = [
  {
    key: "library",
    label: "Library",
    icon: Library,
    items: [
      { id: "tags", label: "Tags", icon: Tag },
      { id: "style", label: "Styles", icon: Palette },
    ],
  },
  {
    key: "project",
    label: "Project",
    icon: FolderCog,
    items: [
      { id: "presets", label: "Render Presets", icon: SlidersHorizontal },
      { id: "youtube", label: "YouTube", icon: Upload },
    ],
  },
];

const UTILITY_ITEMS: NavItem[] = [
  { id: "prompts", label: "Prompts", icon: FileText },
  { id: "settings", label: "Settings", icon: Settings },
  { id: "trash", label: "Trash", icon: Trash2 },
];

const STORAGE_KEY = "manageSidebarCollapsed";
const COLLAPSED_GROUPS_KEY = "manageSidebarCollapsedGroups";

// ── Component ────────────────────────────────────────────────

export default function ManageSidebar({
  activeTab,
  onTabChange,
}: {
  activeTab: ManageTab;
  onTabChange: (tab: ManageTab) => void;
}) {
  const projectId = useStudioStore((s) => s.projectId);
  const projects = useStudioStore((s) => s.projects);
  const projectName = projects.find((p) => p.id === projectId)?.name ?? null;

  const [collapsed, setCollapsed] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  // Hydrate from localStorage
  useEffect(() => {
    setCollapsed(localStorage.getItem(STORAGE_KEY) === "true");
    const saved = localStorage.getItem(COLLAPSED_GROUPS_KEY);
    if (saved) {
      try {
        setCollapsedGroups(new Set(JSON.parse(saved)));
      } catch {
        /* ignore */
      }
    }
  }, []);

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
      localStorage.setItem(COLLAPSED_GROUPS_KEY, JSON.stringify([...next]));
      return next;
    });
  }, []);

  const sidebarWidth = collapsed ? "w-14" : "w-56";

  return (
    <aside
      className={cx(
        "hidden flex-col border-r border-zinc-200 bg-white transition-[width] duration-200 lg:flex",
        sidebarWidth
      )}
    >
      {/* Scrollable nav */}
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV_GROUPS.map((group) => {
          const isGroupCollapsed = collapsedGroups.has(group.key);
          return (
            <div key={group.key} className="mb-1">
              {/* Group header */}
              {!collapsed && (
                <button
                  onClick={() => toggleGroup(group.key)}
                  className={cx(
                    LABEL_CLASSES,
                    "flex w-full items-center gap-1 px-4 pt-4 pb-1 transition hover:text-zinc-600"
                  )}
                >
                  <ChevronDown
                    className={cx("h-3 w-3 transition-transform", isGroupCollapsed && "-rotate-90")}
                  />
                  {group.label}
                  {group.key === "project" && projectName && (
                    <span className="ml-auto max-w-[7rem] truncate text-[9px] font-medium text-zinc-400">
                      {projectName}
                    </span>
                  )}
                </button>
              )}
              {/* Items */}
              {(!isGroupCollapsed || collapsed) && (
                <ul className="space-y-0.5 px-1.5">
                  {group.items.map((item) => (
                    <NavItemButton
                      key={item.id}
                      item={item}
                      active={activeTab === item.id}
                      collapsed={collapsed}
                      onClick={() => onTabChange(item.id)}
                    />
                  ))}
                </ul>
              )}
            </div>
          );
        })}

        {/* Divider */}
        <div className="mx-3 my-2 border-t border-zinc-100" />

        {/* Utility items */}
        <ul className="space-y-0.5 px-1.5">
          {UTILITY_ITEMS.map((item) => (
            <NavItemButton
              key={item.id}
              item={item}
              active={activeTab === item.id}
              collapsed={collapsed}
              onClick={() => onTabChange(item.id)}
            />
          ))}
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

// ── Nav item button ──────────────────────────────────────────

function NavItemButton({
  item,
  active,
  collapsed,
  onClick,
}: {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
  onClick: () => void;
}) {
  const Icon = item.icon;
  return (
    <li>
      <button
        onClick={onClick}
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
}
