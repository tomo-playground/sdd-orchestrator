"use client";

import { Users, Palette, Mic, Music, Boxes, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import SubNavShell, { type SubNavTab } from "./SubNavShell";

const TABS: SubNavTab[] = [
  { href: "/library/characters", label: "캐릭터", icon: Users },
  { href: "/library/styles", label: "화풍", icon: Palette },
  { href: "/library/voices", label: "음성", icon: Mic },
  { href: "/library/music", label: "BGM", icon: Music },
  { href: "/library/loras", label: "LoRAs", icon: Boxes },
];

const TRASH_LINK: SubNavTab = {
  href: "/library/trash",
  label: "휴지통",
  icon: Trash2,
};

export default function LibraryShell({ children }: { children: ReactNode }) {
  return <SubNavShell tabs={TABS} footerLink={TRASH_LINK}>{children}</SubNavShell>;
}
