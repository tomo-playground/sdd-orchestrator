"use client";

import { TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";

type TabItem = {
    id: string;
    label: string;
};

type AppMobileTabBarProps = {
    tabs: TabItem[];
    activeTab: string;
    onTabChange: (tab: any) => void;
};

export default function AppMobileTabBar({
    tabs,
    activeTab,
    onTabChange,
}: AppMobileTabBarProps) {
    return (
        <div className="fixed top-[var(--nav-height)] right-0 left-0 z-[var(--z-sticky)] flex gap-1 overflow-x-auto border-b border-zinc-200 bg-white/90 px-4 py-1.5 backdrop-blur-md lg:hidden">
            {tabs.map((tab) => {
                const active = activeTab === tab.id;
                return (
                    <button
                        key={tab.id}
                        type="button"
                        onClick={() => onTabChange(tab.id)}
                        className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${active ? TAB_ACTIVE : TAB_INACTIVE
                            }`}
                    >
                        {tab.label}
                    </button>
                );
            })}
        </div>
    );
}
