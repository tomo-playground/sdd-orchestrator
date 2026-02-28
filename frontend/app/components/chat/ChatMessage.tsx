"use client";

import { memo } from "react";
import UserBubble from "./messages/UserBubble";
import AssistantBubble from "./messages/AssistantBubble";
import SettingsRecommendCard from "./messages/SettingsRecommendCard";
import ConceptCard from "./messages/ConceptCard";
import ReviewCard from "./messages/ReviewCard";
import CompletionCard from "./messages/CompletionCard";
import ErrorCard from "./messages/ErrorCard";
import type { ChatMessage as ChatMessageType, SettingsRecommendation } from "../../types/chat";
import type { SceneItem, ResumeOptions } from "../../hooks/scriptEditor/types";
import type { FeedbackPreset } from "../../types";
import type { Preset, LangOption } from "../../hooks/usePresets";
import type { ScriptMode } from "./ModeChips";

export type ChatMessageCallbacks = {
  onApplyAndGenerate: (rec: SettingsRecommendation) => void;
  onResume: (
    action: "approve" | "revise" | "select" | "regenerate" | "custom_concept",
    feedback?: string,
    conceptId?: number,
    options?: ResumeOptions
  ) => void;
  onRetry: () => void;
  onNavigate: (tab: string) => void;
  onPresetChange: (preset: string, skipStages: string[]) => void;
};

export type ChatMessageData = {
  scenes: SceneItem[];
  feedbackPresets: FeedbackPreset[] | null;
  presets: Preset[];
  languages: LangOption[];
  durations: number[];
  currentMode: ScriptMode;
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
    case "settings_recommend":
      return (
        <SettingsRecommendCard
          message={message}
          onApplyAndGenerate={callbacks.onApplyAndGenerate}
          presets={data.presets}
          languages={data.languages}
          durations={data.durations}
          currentMode={data.currentMode}
          onPresetChange={callbacks.onPresetChange}
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
    case "error":
      return <ErrorCard message={message.errorMessage} onRetry={callbacks.onRetry} />;
    default:
      return null;
  }
});

export default ChatMessage;
