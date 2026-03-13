"use client";

import { SlidersHorizontal, Youtube, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import SubNavShell, { type SubNavTab } from "./SubNavShell";

const TABS: SubNavTab[] = [
  { href: "/settings/presets", label: "Render Presets", icon: SlidersHorizontal },
  { href: "/settings/youtube", label: "YouTube", icon: Youtube },
  { href: "/settings/trash", label: "Trash", icon: Trash2 },
];

export default function SettingsShell({ children }: { children: ReactNode }) {
  return <SubNavShell tabs={TABS}>{children}</SubNavShell>;
}
