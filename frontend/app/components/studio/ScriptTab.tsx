"use client";

import { useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useChatScriptEditor } from "../../hooks/useChatScriptEditor";
import { useUIStore } from "../../store/useUIStore";
import { useContextStore } from "../../store/useContextStore";
import ChatArea from "../chat/ChatArea";

export default function ScriptTab() {
  const router = useRouter();
  const storyboardId = useContextStore((s) => s.storyboardId);
  const onSaved = useCallback(
    (id: number) => {
      router.replace(`/studio?id=${id}`);
      useUIStore.getState().setActiveTab("stage");
      useUIStore.getState().setPendingAutoRun(true);
    },
    [router]
  );
  const editor = useChatScriptEditor({ onSaved });

  // Load storyboard when contextStore storyboardId changes
  const loadedRef = useRef<number | null>(null);
  useEffect(() => {
    if (storyboardId && loadedRef.current !== storyboardId) {
      loadedRef.current = storyboardId;
      editor.loadStoryboard(storyboardId);
    } else if (!storyboardId && loadedRef.current !== null) {
      loadedRef.current = null;
      editor.clearChat();
    }
  }, [storyboardId]); // eslint-disable-line react-hooks/exhaustive-deps

  return <ChatArea editor={editor} />;
}
