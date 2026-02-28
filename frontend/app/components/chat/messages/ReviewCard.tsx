"use client";

import { Bot } from "lucide-react";
import ReviewApprovalPanel from "../../scripts/ReviewApprovalPanel";
import type { ChatMessage } from "../../../types/chat";
import type { ChatScriptEditorActions } from "../../../hooks/useChatScriptEditor";

type Props = {
  message: ChatMessage;
  editor: ChatScriptEditorActions;
};

export default function ReviewCard({ message, editor }: Props) {
  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="min-w-0 flex-1">
        <ReviewApprovalPanel
          scenes={editor.scenes}
          onApprove={() => editor.resume("approve")}
          onRevise={(feedback) => editor.resume("revise", feedback)}
          feedbackPresets={editor.feedbackPresets ?? undefined}
          onPresetRevise={(presetId, params) =>
            editor.resume("revise", undefined, undefined, {
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
