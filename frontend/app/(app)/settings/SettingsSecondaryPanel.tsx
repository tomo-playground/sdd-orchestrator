"use client";

import { Brain, SlidersHorizontal, Upload, Settings, Trash2, type LucideIcon } from "lucide-react";
import { SIDE_PANEL_CLASSES, SIDE_PANEL_LABEL } from "../../components/ui/variants";
import type { SettingsTab } from "./types";

type TabHelp = {
  icon: LucideIcon;
  title: string;
  description: string;
  notes: string[];
};

const HELP: Record<SettingsTab, TabHelp> = {
  general: {
    icon: Settings,
    title: "Settings",
    description: "General project and system settings.",
    notes: [
      "API keys are stored in .env",
      "Refresh caches after config changes",
      "Check system health periodically",
    ],
  },
  presets: {
    icon: SlidersHorizontal,
    title: "Render Presets",
    description: "Configure video rendering presets.",
    notes: [
      "Presets define resolution, FPS, codec",
      "Create presets per content type",
      "Default preset is used for quick renders",
    ],
  },
  youtube: {
    icon: Upload,
    title: "YouTube",
    description: "Manage YouTube upload settings and credentials.",
    notes: [
      "OAuth2 authentication required",
      "Set default privacy and category",
      "Schedule uploads for optimal timing",
    ],
  },
  trash: {
    icon: Trash2,
    title: "Trash",
    description: "View and restore soft-deleted items.",
    notes: [
      "Items are soft-deleted (recoverable)",
      "Permanent deletion after 30 days",
      "Restore to original location",
    ],
  },
  memory: {
    icon: Brain,
    title: "AI Memory",
    description: "AI agent memory store management.",
    notes: [
      "Character, topic, user memories",
      "Delete individual items or namespaces",
      "Memory is used for context-aware generation",
    ],
  },
};

export default function SettingsSecondaryPanel({ activeTab }: { activeTab: SettingsTab }) {
  const help = HELP[activeTab];
  const Icon = help.icon;

  return (
    <div className={SIDE_PANEL_CLASSES}>
      <span className={SIDE_PANEL_LABEL}>
        <Icon className="mr-1 inline h-3 w-3" />
        {help.title}
      </span>
      <p className="text-xs leading-relaxed text-zinc-500">{help.description}</p>
      <div className="space-y-1.5 pt-1">
        <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
          Notes
        </span>
        <ul className="space-y-1">
          {help.notes.map((note, i) => (
            <li key={i} className="flex items-start gap-1.5 text-xs text-zinc-600">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-zinc-300" />
              {note}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
