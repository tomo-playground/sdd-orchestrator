"use client";

import { Bot } from "lucide-react";
import ConceptSelectionPanel from "../../scripts/ConceptSelectionPanel";
import type { ChatMessage } from "../../../types/chat";
import type { ResumeOptions } from "../../../hooks/scriptEditor/types";

type Props = {
  message: ChatMessage;
  onResume: (
    action: "approve" | "revise" | "select" | "regenerate" | "custom_concept",
    feedback?: string,
    conceptId?: number,
    options?: ResumeOptions
  ) => void;
};

export default function ConceptCard({ message, onResume }: Props) {
  if (!message.concepts || message.concepts.length === 0) return null;

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="min-w-0 flex-1">
        <ConceptSelectionPanel
          candidates={message.concepts}
          recommendedId={message.recommendedConceptId ?? null}
          onSelect={(conceptId) => onResume("select", undefined, conceptId)}
          onRegenerate={() => onResume("regenerate")}
          onCustomConcept={(concept) =>
            onResume("custom_concept", undefined, undefined, { customConcept: concept })
          }
        />
      </div>
    </div>
  );
}
