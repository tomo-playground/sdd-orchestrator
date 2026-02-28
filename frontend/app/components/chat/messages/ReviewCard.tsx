"use client";

import { Bot } from "lucide-react";
import ReviewApprovalPanel from "../../scripts/ReviewApprovalPanel";
import type { ChatMessage } from "../../../types/chat";
import type { SceneItem, ResumeOptions } from "../../../hooks/scriptEditor/types";
import type { FeedbackPreset } from "../../../types";

type Props = {
  message: ChatMessage;
  scenes: SceneItem[];
  feedbackPresets: FeedbackPreset[] | null;
  onResume: (
    action: "approve" | "revise" | "select" | "regenerate" | "custom_concept",
    feedback?: string,
    conceptId?: number,
    options?: ResumeOptions
  ) => void;
};

export default function ReviewCard({ message, scenes, feedbackPresets, onResume }: Props) {
  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="min-w-0 flex-1">
        <ReviewApprovalPanel
          scenes={scenes}
          onApprove={() => onResume("approve")}
          onRevise={(feedback) => onResume("revise", feedback)}
          feedbackPresets={feedbackPresets ?? undefined}
          onPresetRevise={(presetId, params) =>
            onResume("revise", undefined, undefined, {
              feedbackPreset: presetId,
              feedbackPresetParams: params,
            })
          }
          reviewResult={message.reviewResult}
          productionSnapshot={message.productionSnapshot ?? undefined}
        />
      </div>
    </div>
  );
}
