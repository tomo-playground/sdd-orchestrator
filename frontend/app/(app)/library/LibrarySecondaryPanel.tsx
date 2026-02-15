"use client";

import { Users, Mic, Music, Image, type LucideIcon } from "lucide-react";
import { SIDE_PANEL_CLASSES, SIDE_PANEL_LABEL } from "../../components/ui/variants";
import type { LibraryTab } from "./types";

type TabGuide = {
  icon: LucideIcon;
  title: string;
  description: string;
  tips: string[];
};

const GUIDES: Record<LibraryTab, TabGuide> = {
  characters: {
    icon: Users,
    title: "Characters",
    description: "Create and manage character profiles for consistent visual generation.",
    tips: [
      "Add a LoRA model for best likeness",
      "Lock preview to fix the reference image",
      "Use custom base prompt for style override",
    ],
  },
  voices: {
    icon: Mic,
    title: "Voices",
    description: "Generate and manage voice presets for narration.",
    tips: [
      "Describe the voice personality in detail",
      "Preview before saving to check quality",
      "One preset can be reused across storyboards",
    ],
  },
  music: {
    icon: Music,
    title: "Music",
    description: "Create background music presets with AI generation.",
    tips: [
      "Use genre + mood keywords in prompt",
      "Max duration is 47 seconds per clip",
      "Preview to test before adding to a scene",
    ],
  },
  backgrounds: {
    icon: Image,
    title: "Backgrounds",
    description: "Upload reference backgrounds for scene generation.",
    tips: [
      "Tag backgrounds for better auto-matching",
      "Use categories to organize by location",
      "Higher weight = stronger visual influence",
    ],
  },
};

export default function LibrarySecondaryPanel({ activeTab }: { activeTab: LibraryTab }) {
  const guide = GUIDES[activeTab];
  const Icon = guide.icon;

  return (
    <div className={SIDE_PANEL_CLASSES}>
      <span className={SIDE_PANEL_LABEL}>
        <Icon className="mr-1 inline h-3 w-3" />
        {guide.title} Guide
      </span>
      <p className="text-xs leading-relaxed text-zinc-500">{guide.description}</p>
      <div className="space-y-1.5 pt-1">
        <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
          Tips
        </span>
        <ul className="space-y-1">
          {guide.tips.map((tip, i) => (
            <li key={i} className="flex items-start gap-1.5 text-xs text-zinc-600">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-zinc-300" />
              {tip}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
