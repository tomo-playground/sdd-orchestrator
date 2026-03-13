"use client";

import { Users, Palette, Mic, Music, Boxes } from "lucide-react";
import type { ReactNode } from "react";
import SubNavShell, { type SubNavTab } from "./SubNavShell";

const TABS: SubNavTab[] = [
  { href: "/library/characters", label: "Characters", icon: Users },
  { href: "/library/styles", label: "Styles", icon: Palette },
  { href: "/library/voices", label: "Voices", icon: Mic },
  { href: "/library/music", label: "Music", icon: Music },
  { href: "/library/loras", label: "LoRAs", icon: Boxes },
];

export default function LibraryShell({ children }: { children: ReactNode }) {
  return <SubNavShell tabs={TABS}>{children}</SubNavShell>;
}
