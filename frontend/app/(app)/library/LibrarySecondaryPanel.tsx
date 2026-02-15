"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Users, Mic, Music, Image, Tag, Palette, FileText, type LucideIcon } from "lucide-react";
import axios from "axios";
import { SIDE_PANEL_CLASSES, SIDE_PANEL_LABEL } from "../../components/ui/variants";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import type { LibraryTab } from "./types";
import { API_BASE } from "../../constants";

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
  tags: {
    icon: Tag,
    title: "Tags",
    description: "Manage Danbooru-standard tags for prompt generation.",
    tips: [
      "Tags use underscore format (brown_hair)",
      "Check pending tags for review",
      "Tag rules resolve conflicts automatically",
    ],
  },
  style: {
    icon: Palette,
    title: "Styles",
    description: "Configure SD models, samplers, and generation settings.",
    tips: [
      "SD WebUI must be running with --api",
      "Refresh to sync available models",
      "Styles are project-scoped",
    ],
  },
  prompts: {
    icon: FileText,
    title: "Prompts",
    description: "View and manage prompt templates.",
    tips: [
      "Templates use Jinja2 syntax",
      "12-Layer Builder composes final prompts",
      "Test with Prompt Validate command",
    ],
  },
};

type Character = {
  id: number;
  name: string;
  gender: string;
  base_prompt: string | null;
  lora_name: string | null;
  lora_weight: number | null;
  preview_locked: boolean;
  preview_url: string | null;
};

export default function LibrarySecondaryPanel({ activeTab }: { activeTab: LibraryTab }) {
  const searchParams = useSearchParams();
  const characterId = searchParams.get("id");
  const [character, setCharacter] = useState<Character | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeTab === "characters" && characterId) {
      setLoading(true);
      axios
        .get(`${API_BASE}/characters/${characterId}`)
        .then((res) => setCharacter(res.data))
        .catch((err) => console.error("Failed to load character:", err))
        .finally(() => setLoading(false));
    } else {
      setCharacter(null);
    }
  }, [activeTab, characterId]);

  // Show character details if id parameter is present
  if (activeTab === "characters" && characterId) {
    if (loading) {
      return (
        <div className={SIDE_PANEL_CLASSES}>
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="sm" />
          </div>
        </div>
      );
    }

    if (!character) {
      return (
        <div className={SIDE_PANEL_CLASSES}>
          <span className={SIDE_PANEL_LABEL}>
            <Users className="mr-1 inline h-3 w-3" />
            Character Not Found
          </span>
          <p className="text-xs text-zinc-500">
            Unable to load character details.
          </p>
        </div>
      );
    }

    return (
      <div className={SIDE_PANEL_CLASSES}>
        <span className={SIDE_PANEL_LABEL}>
          <Users className="mr-1 inline h-3 w-3" />
          Character Details
        </span>

        {character.preview_url && (
          <div className="mb-3 overflow-hidden rounded-lg border border-zinc-200">
            <img
              src={character.preview_url}
              alt={character.name}
              className="h-auto w-full"
            />
          </div>
        )}

        <div className="space-y-2">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
              Name
            </span>
            <p className="text-sm text-zinc-900">{character.name}</p>
          </div>

          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
              Gender
            </span>
            <p className="text-sm text-zinc-900">{character.gender}</p>
          </div>

          {character.lora_name && (
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                LoRA
              </span>
              <p className="text-sm text-zinc-900">
                {character.lora_name}
                {character.lora_weight && ` (${character.lora_weight})`}
              </p>
            </div>
          )}

          {character.base_prompt && (
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                Base Prompt
              </span>
              <p className="text-xs leading-relaxed text-zinc-600">
                {character.base_prompt}
              </p>
            </div>
          )}

          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
              Preview
            </span>
            <p className="text-sm text-zinc-900">
              {character.preview_locked ? "🔒 Locked" : "🔓 Unlocked"}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Default: show guide
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
