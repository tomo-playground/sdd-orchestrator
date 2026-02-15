import { ReactNode } from "react";
import {
    STUDIO_3COL_LAYOUT,
    LEFT_PANEL_CLASSES,
    CENTER_PANEL_CLASSES,
    RIGHT_PANEL_CLASSES,
} from "../ui/variants";

interface StudioThreeColumnLayoutProps {
    leftPanel: ReactNode;
    centerPanel: ReactNode;
    rightPanel: ReactNode;
}

export default function StudioThreeColumnLayout({
    leftPanel,
    centerPanel,
    rightPanel,
}: StudioThreeColumnLayoutProps) {
    return (
        <div className={STUDIO_3COL_LAYOUT}>
            <aside className={LEFT_PANEL_CLASSES}>{leftPanel}</aside>
            <main className={CENTER_PANEL_CLASSES}>{centerPanel}</main>
            <aside className={RIGHT_PANEL_CLASSES}>{rightPanel}</aside>
        </div>
    );
}
