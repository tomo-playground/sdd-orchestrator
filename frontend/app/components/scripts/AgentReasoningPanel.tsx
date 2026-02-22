"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Brain,
  Eye,
  Megaphone,
  FileText,
  Camera,
  Mic,
  Music,
  Shield,
} from "lucide-react";
import { renderSectionContent } from "./reasoning/ReasoningSections";

type Props = {
  nodeResults: Record<string, Record<string, unknown>>;
  expandedStep?: string | null;
  onToggle?: (stepId: string | null) => void;
  skipStages: string[];
};

type SectionDef = {
  id: string;
  label: string;
  icon: React.ReactNode;
  stage?: string;
};

const SECTIONS: SectionDef[] = [
  {
    id: "critic",
    label: "Critic 컨셉 토론",
    icon: <Brain className="h-3.5 w-3.5" />,
    stage: "concept",
  },
  { id: "review", label: "Review 구조 검증", icon: <Eye className="h-3.5 w-3.5" /> },
  {
    id: "cinematographer",
    label: "Cinematographer 시각 설계",
    icon: <Camera className="h-3.5 w-3.5" />,
    stage: "production",
  },
  {
    id: "tts_designer",
    label: "TTS Designer 음성 설계",
    icon: <Mic className="h-3.5 w-3.5" />,
    stage: "production",
  },
  {
    id: "sound_designer",
    label: "Sound Designer BGM 추천",
    icon: <Music className="h-3.5 w-3.5" />,
    stage: "production",
  },
  {
    id: "copyright_reviewer",
    label: "Copyright 저작권 검증",
    icon: <Shield className="h-3.5 w-3.5" />,
    stage: "production",
  },
  {
    id: "director",
    label: "Director 통합 검증",
    icon: <Megaphone className="h-3.5 w-3.5" />,
    stage: "production",
  },
  {
    id: "explain",
    label: "Explain 결정 설명",
    icon: <FileText className="h-3.5 w-3.5" />,
    stage: "explain",
  },
];

export default function AgentReasoningPanel({
  nodeResults,
  expandedStep,
  onToggle,
  skipStages,
}: Props) {
  const [localExpanded, setLocalExpanded] = useState<string | null>(null);
  const expanded = expandedStep !== undefined ? expandedStep : localExpanded;
  const toggle =
    onToggle ?? ((id: string | null) => setLocalExpanded((prev) => (prev === id ? null : id)));

  const skipSet = new Set(skipStages);
  const visibleSections = SECTIONS.filter(
    (s) => (!s.stage || !skipSet.has(s.stage)) && nodeResults[s.id]
  );

  if (visibleSections.length === 0) return null;

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4">
      <h3 className="mb-3 text-xs font-semibold text-zinc-500">AI 판단 근거</h3>
      <div className="space-y-1">
        {visibleSections.map((section) => {
          const isOpen = expanded === section.id;
          return (
            <div key={section.id}>
              <button
                type="button"
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-zinc-50"
                onClick={() => toggle(isOpen ? null : section.id)}
              >
                {isOpen ? (
                  <ChevronDown className="h-3.5 w-3.5 text-zinc-400" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5 text-zinc-400" />
                )}
                {section.icon}
                <span className="text-xs font-medium text-zinc-700">{section.label}</span>
              </button>
              {isOpen && (
                <div className="mt-1 mb-2 ml-8">
                  {renderSectionContent(section.id, nodeResults[section.id])}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
