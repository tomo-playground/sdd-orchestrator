"use client";

import { memo } from "react";
import UserBubble from "./messages/UserBubble";
import AssistantBubble from "./messages/AssistantBubble";
import SettingsRecommendCard from "./messages/SettingsRecommendCard";
import ConceptCard from "./messages/ConceptCard";
import ReviewCard from "./messages/ReviewCard";
import CompletionCard from "./messages/CompletionCard";
import ErrorCard from "./messages/ErrorCard";
import type { ChatMessage as ChatMessageType } from "../../types/chat";
import type { ChatScriptEditorActions } from "../../hooks/useChatScriptEditor";

type Props = {
  message: ChatMessageType;
  editor: ChatScriptEditorActions;
};

const ChatMessage = memo(function ChatMessage({ message, editor }: Props) {
  switch (message.contentType) {
    case "user":
      return <UserBubble text={message.text ?? ""} />;
    case "assistant":
      return <AssistantBubble text={message.text ?? ""} />;
    case "settings_recommend":
      return <SettingsRecommendCard message={message} onApply={editor.applyRecommendation} />;
    case "concept_gate":
      return <ConceptCard message={message} editor={editor} />;
    case "review_gate":
      return <ReviewCard message={message} editor={editor} />;
    case "completion":
      return <CompletionCard text={message.text ?? ""} sceneCount={editor.scenes.length} />;
    case "error":
      return <ErrorCard message={message.errorMessage} onRetry={editor.confirmAndGenerate} />;
    default:
      return null;
  }
});

export default ChatMessage;
