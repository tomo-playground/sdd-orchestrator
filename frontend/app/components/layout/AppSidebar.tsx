"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, type LucideIcon, ChevronDown } from "lucide-react";
import { cx, LABEL_CLASSES, SIDEBAR_ACTIVE, SIDEBAR_INACTIVE } from "../ui/variants";

// ── Types ────────────────────────────────────────────────────

export type NavItem = {
    id: string;
    label: string;
    icon: LucideIcon;
};

export type NavGroup = {
    key: string;
    label: string;
    items: NavItem[];
};

export type AppSidebarProps = {
    groups?: NavGroup[];
    items?: NavItem[]; // Fallback for simple lists without groups
    ungroupedItems?: NavItem[]; // Items at the bottom (like utilities)
    activeTab: string;
    onTabChange: (tab: any) => void;
    collapsedKey: string;
    collapsedGroupsKey?: string;
    headerContent?: ReactNode;
};

// ── Component ────────────────────────────────────────────────

export default function AppSidebar({
    groups = [],
    items = [],
    ungroupedItems = [],
    activeTab,
    onTabChange,
    collapsedKey,
    collapsedGroupsKey,
    headerContent,
}: AppSidebarProps) {
    const [collapsed, setCollapsed] = useState(false);
    const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

    // Hydrate from localStorage
    useEffect(() => {
        setCollapsed(localStorage.getItem(collapsedKey) === "true");

        if (collapsedGroupsKey) {
            const saved = localStorage.getItem(collapsedGroupsKey);
            if (saved) {
                try {
                    setCollapsedGroups(new Set(JSON.parse(saved)));
                } catch {
                    /* ignore */
                }
            }
        }
    }, [collapsedKey, collapsedGroupsKey]);

    const toggleCollapse = useCallback(() => {
        setCollapsed((prev) => {
            const next = !prev;
            localStorage.setItem(collapsedKey, String(next));
            return next;
        });
    }, [collapsedKey]);

    const toggleGroup = useCallback((key: string) => {
        if (!collapsedGroupsKey) return;

        setCollapsedGroups((prev) => {
            const next = new Set(prev);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            localStorage.setItem(collapsedGroupsKey, JSON.stringify([...next]));
            return next;
        });
    }, [collapsedGroupsKey]);

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
            {/* Scrollable nav */}
            <nav className="flex-1 overflow-y-auto pl-5 pr-3 py-3">
                {/* Simple List (if no groups provided) */}
                {groups.length === 0 && items.length > 0 && (
                    <ul className="space-y-0.5">
                        {items.map((item) => (
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

                {/* Groups */}
                {groups.map((group) => {
                    const isGroupCollapsed = collapsedGroups.has(group.key);
                    return (
                        <div key={group.key} className="mb-1">
                            {/* Group header */}
                            {!collapsed && (
                                <button
                                    onClick={() => toggleGroup(group.key)}
                                    className={cx(
                                        LABEL_CLASSES,
                                        "flex w-full items-center gap-1 pl-5 pr-3 pt-4 pb-1 transition hover:text-zinc-600"
                                    )}
                                >
                                    <ChevronDown
                                        className={cx("h-3 w-3 transition-transform", isGroupCollapsed && "-rotate-90")}
                                    />
                                    {group.label}
                                    {group.key === "project" && headerContent}
                                </button>
                            )}
                            {/* Items */}
                            {(!isGroupCollapsed || collapsed) && (
                                <ul className="space-y-0.5">
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

                {/* Divider if needed */}
                {(groups.length > 0 || items.length > 0) && ungroupedItems.length > 0 && (
                    <div className="mx-3 my-2 border-t border-zinc-100" />
                )}

                {/* Ungrouped/Utility items */}
                {ungroupedItems.length > 0 && (
                    <ul className="space-y-0.5">
                        {ungroupedItems.map((item) => (
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
                    "flex w-full items-center gap-2.5 rounded-lg px-3 py-1.5 text-xs transition",
                    active ? SIDEBAR_ACTIVE : SIDEBAR_INACTIVE,
                    collapsed && "justify-center px-0"
                )}
            >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
            </button>
        </li>
    );
}
