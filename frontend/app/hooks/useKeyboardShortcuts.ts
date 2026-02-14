"use client";

import { useEffect } from "react";

type ShortcutHandler = (e: KeyboardEvent) => void;

type ShortcutConfig = {
    key: string;
    metaKey?: boolean; // Cmd on Mac, Ctrl on Windows
    ctrlKey?: boolean;
    shiftKey?: boolean;
    altKey?: boolean;
    action: () => void;
    preventDefault?: boolean;
};

export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]) {
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Ignore if user is typing in an input/textarea, unless it's a modifier combo like Cmd+S
            const target = e.target as HTMLElement;
            const isInput =
                target.tagName === "INPUT" ||
                target.tagName === "TEXTAREA" ||
                target.isContentEditable;

            for (const config of shortcuts) {
                if (e.key.toLowerCase() === config.key.toLowerCase()) {
                    const metaMatch = !!config.metaKey === (e.metaKey || e.ctrlKey); // Treat Ctrl as Meta on Windows/Linux usually, but here we can be specific if needed.
                    // Note: e.metaKey is Cmd on Mac. e.ctrlKey is Ctrl.
                    // For cross-platform "Cmd/Ctrl + S", we usually check (e.metaKey || e.ctrlKey).

                    const ctrlMatch = config.ctrlKey !== undefined ? config.ctrlKey === e.ctrlKey : true;
                    const shiftMatch = config.shiftKey !== undefined ? config.shiftKey === e.shiftKey : true;
                    const altMatch = config.altKey !== undefined ? config.altKey === e.altKey : true;

                    // For Meta combinations, we allow execution even in inputs (e.g. Cmd+S)
                    // For single keys, we block in inputs
                    const isModifierCombo = config.metaKey || config.ctrlKey || config.altKey;

                    if (!isModifierCombo && isInput) {
                        continue;
                    }

                    if (metaMatch && ctrlMatch && shiftMatch && altMatch) {
                        if (config.preventDefault !== false) {
                            e.preventDefault();
                        }
                        config.action();
                        return; // Execute only one match
                    }
                }
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [shortcuts]);
}
