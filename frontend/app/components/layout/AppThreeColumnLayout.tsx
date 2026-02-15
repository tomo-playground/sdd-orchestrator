import { ReactNode } from "react";

interface AppThreeColumnLayoutProps {
    left: ReactNode;
    center: ReactNode;
    right: ReactNode;
}

/**
 * Shared layout for Manage and Library pages.
 * Supports a collapsible left sidebar (handled by the passed 'left' component),
 * a flexible center content area, and a fixed-width right panel.
 */
export default function AppThreeColumnLayout({
    left,
    center,
    right,
}: AppThreeColumnLayoutProps) {
    return (
        <div className="flex h-full w-full overflow-hidden bg-white">
            {/* Left Panel (Sidebar) - Width is controlled by the component itself (collapsible) */}
            {left}

            {/* Center Panel - Flexible width, independent scroll */}
            <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-white">
                <div className="h-full w-full overflow-y-auto">
                    {center}
                </div>
            </main>

            {/* Right Panel - Fixed width, sticky-like behavior but implemented as a flex column */}
            <aside className="flex w-[300px] flex-none flex-col border-l border-zinc-200 bg-zinc-50/50 overflow-hidden">
                <div className="h-full w-full overflow-y-auto p-4 space-y-4">
                    {right}
                </div>
            </aside>
        </div>
    );
}
