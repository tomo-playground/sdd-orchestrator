"use client";

import { SlidersHorizontal, Youtube, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import SubNavShell, { type SubNavTab } from "./SubNavShell";

const TABS: SubNavTab[] = [
  { href: "/settings/presets", label: "렌더 설정", icon: SlidersHorizontal },
  { href: "/settings/youtube", label: "연동", icon: Youtube },
  { href: "/settings/trash", label: "휴지통", icon: Trash2 },
];

export default function SettingsShell({ children }: { children: ReactNode }) {
  return <SubNavShell tabs={TABS}>{children}</SubNavShell>;
}
