"use client";

import { memo } from "react";
import UserBubble from "./messages/UserBubble";
import AssistantBubble from "./messages/AssistantBubble";
import SettingsRecommendCard from "./messages/SettingsRecommendCard";
import ClarificationCard from "./messages/ClarificationCard";
import ConceptCard from "./messages/ConceptCard";
import ReviewCard from "./messages/ReviewCard";
import CompletionCard from "./messages/CompletionCard";
import ErrorCard from "./messages/ErrorCard";
import PipelineStepCard from "./messages/PipelineStepCard";
import PlanReviewCard from "./messages/PlanReviewCard";
import SceneEditDiffCard from "./messages/SceneEditDiffCard";
import type { ChatMessage as ChatMessageType, SettingsRecommendation } from "../../types/chat";
import type { SceneItem, ResumeOptions, ResumeAction } from "../../hooks/scriptEditor/types";
import type { FeedbackPreset } from "../../types";

const noop = () => {};

export type ChatMessageCallbacks = {
  onApplyAndGenerate: (rec: SettingsRecommendation) => void;
  onResume: (
    action: ResumeAction,
    feedback?: string,
    conceptId?: number,
    options?: ResumeOptions
  ) => void;
  onRetry: () => void;
  onNavigate: (tab: string) => void;
  onSendMessage?: (text: string) => void;
  onAcceptEdit?: () => void;
  onRejectEdit?: () => void;
};

export type ChatMessageData = {
  scenes: SceneItem[];
  feedbackPresets: FeedbackPreset[] | null;
};

type Props = {
  message: ChatMessageType;
  callbacks: ChatMessageCallbacks;
  data: ChatMessageData;
};

const ChatMessage = memo(function ChatMessage({ message, callbacks, data }: Props) {
  switch (message.contentType) {
    case "user":
      return <UserBubble text={message.text ?? ""} />;
    case "assistant":
      return <AssistantBubble text={message.text ?? ""} />;
    case "clarification":
      return <ClarificationCard message={message} />;
    case "settings_recommend":
      return (
        <SettingsRecommendCard
          message={message}
          onApplyAndGenerate={callbacks.onApplyAndGenerate}
        />
      );
    case "concept_gate":
      return <ConceptCard message={message} onResume={callbacks.onResume} />;
    case "review_gate":
      return (
        <ReviewCard
          message={message}
          scenes={data.scenes}
          feedbackPresets={data.feedbackPresets}
          onResume={callbacks.onResume}
        />
      );
    case "completion":
      return (
        <CompletionCard
          text={message.text ?? ""}
          sceneCount={data.scenes.length}
          onNavigate={callbacks.onNavigate}
        />
      );
    case "pipeline_step":
      return <PipelineStepCard message={message} />;
    case "plan_review_gate":
      return <PlanReviewCard message={message} onResume={callbacks.onResume} />;
    case "scene_edit_diff":
      return message.editResult ? (
        <SceneEditDiffCard
          editResult={message.editResult}
          scenes={data.scenes}
          onAccept={callbacks.onAcceptEdit ?? noop}
          onReject={callbacks.onRejectEdit ?? noop}
          isApplied={!!message.editApplied}
        />
      ) : null;
    case "error":
      return <ErrorCard message={message.errorMessage} onRetry={callbacks.onRetry} />;
    default:
      return null;
  }
});

export default ChatMessage;
