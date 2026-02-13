"use client";

import { FileText, Sparkles } from "lucide-react";
import { SIDE_PANEL_LABEL } from "../ui/variants";

type Props = {
  scenesCount: number;
  isAgent: boolean;
};

const MANUAL_TIPS = [
  "Write a topic that hooks in the first 3 seconds",
  "Keep duration between 30-60s for best engagement",
  "Use Narrated Dialogue for character-driven stories",
  "Add a description to guide the AI tone and style",
];

const AGENT_TIPS = [
  "The AI agent generates script, images, and audio",
  "Review generated scenes before rendering",
  "You can edit individual scenes after generation",
  "Agent mode works best with clear, specific topics",
];

export default function ScriptSidePanel({ scenesCount, isAgent }: Props) {
  const tips = isAgent ? AGENT_TIPS : MANUAL_TIPS;

  return (
    <>
      {/* Status */}
      <div>
        <span className={SIDE_PANEL_LABEL}>
          <FileText className="mr-1 inline h-3 w-3" />
          Status
        </span>
        <div className="mt-2 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-500">Mode</span>
            <span className="font-medium text-zinc-700">{isAgent ? "AI Agent" : "Manual"}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-500">Scenes</span>
            <span className="font-semibold text-zinc-700">{scenesCount}</span>
          </div>
        </div>
      </div>

      {/* Tips */}
      <div className="border-t border-zinc-100 pt-3">
        <span className={SIDE_PANEL_LABEL}>
          <Sparkles className="mr-1 inline h-3 w-3" />
          Tips
        </span>
        <ul className="mt-2 space-y-1.5">
          {tips.map((tip, i) => (
            <li key={i} className="flex items-start gap-1.5 text-xs text-zinc-600">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-zinc-300" />
              {tip}
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
