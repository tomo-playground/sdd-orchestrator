"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { useStudioStore, resetStudioStore } from "../../../store/useStudioStore";
import { API_BASE } from "../../../constants";
import SectionHeader from "./SectionHeader";
import StoryList from "./StoryList";
import AddButton from "./AddButton";
import type { StoryboardItem } from "./StoryList";

type Props = {
  collapsed: boolean;
  groupId: number | null;
};

export default function StudioSections({ collapsed, groupId }: Props) {
  const router = useRouter();
  const storyboardId = useStudioStore((s) => s.storyboardId);
  const setMeta = useStudioStore((s) => s.setMeta);
  const isAutoRunning = useStudioStore((s) => s.isAutoRunning);
  const showToast = useStudioStore((s) => s.showToast);

  const [storyboards, setStoryboards] = useState<StoryboardItem[]>([]);

  useEffect(() => {
    if (!groupId) {
      setStoryboards([]);
      return;
    }
    axios
      .get<StoryboardItem[]>(`${API_BASE}/storyboards`, { params: { group_id: groupId } })
      .then((r) => setStoryboards(r.data))
      .catch(() => setStoryboards([]));
  }, [groupId]);

  const warnAutoRunning = useCallback(() => {
    showToast("Autopilot running — wait for completion", "warning");
  }, [showToast]);

  const handleStorySelect = useCallback(
    (sb: StoryboardItem) => {
      if (isAutoRunning && sb.id !== storyboardId) {
        warnAutoRunning();
        return;
      }
      setMeta({ storyboardId: sb.id, storyboardTitle: sb.title });
      router.push(`/studio?id=${sb.id}`);
    },
    [setMeta, router, isAutoRunning, storyboardId, warnAutoRunning]
  );

  const handleNewStory = useCallback(() => {
    if (isAutoRunning) {
      warnAutoRunning();
      return;
    }
    router.push("/studio?new=true");
  }, [router, isAutoRunning, warnAutoRunning]);

  const handleStoryDelete = useCallback(
    async (id: number) => {
      if (!confirm("Delete this storyboard?")) return;
      try {
        await axios.delete(`${API_BASE}/storyboards/${id}`);
        setStoryboards((prev) => prev.filter((s) => s.id !== id));
        if (storyboardId === id) {
          resetStudioStore();
          router.push("/studio?new=true");
        }
        showToast("Storyboard deleted", "success");
      } catch {
        showToast("Failed to delete", "error");
      }
    },
    [storyboardId, router, showToast]
  );

  return (
    <>
      <SectionHeader
        label="Stories"
        collapsed={collapsed}
        badge={
          isAutoRunning ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900 px-1.5 py-0.5 text-[9px] font-semibold tracking-wider text-white uppercase">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              Running
            </span>
          ) : null
        }
      />
      <StoryList
        storyboards={storyboards}
        activeId={storyboardId}
        collapsed={collapsed}
        locked={isAutoRunning}
        onSelect={handleStorySelect}
        onDelete={handleStoryDelete}
      />
      <AddButton label="New Story" collapsed={collapsed} onClick={handleNewStory} />
    </>
  );
}
