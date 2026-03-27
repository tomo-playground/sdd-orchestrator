"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { Loader2, Plus, Sparkles } from "lucide-react";
import Button from "../ui/Button";
import { useContextStore } from "../../store/useContextStore";
import { useUIStore } from "../../store/useUIStore";
import { API_BASE, API_TIMEOUT } from "../../constants";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function WelcomeBar() {
  const router = useRouter();
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [topic, setTopic] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const projectId = useContextStore((s) => s.projectId);
  const groupId = useContextStore((s) => s.groupId);
  const showToast = useUIStore((s) => s.showToast);

  const canQuickStart = !!projectId && !!groupId;

  useEffect(() => {
    async function fetchCount() {
      try {
        const res = await fetch(`${API_BASE}/storyboards?limit=1`);
        if (!res.ok) return;
        const data = await res.json();
        setTotalCount(data.total ?? 0);
      } catch {
        setTotalCount(0);
      }
    }
    fetchCount();
  }, []);

  async function handleQuickStart() {
    const trimmed = topic.trim();
    if (!trimmed || !groupId) return;

    setIsSubmitting(true);
    try {
      const res = await axios.post<{ storyboard_id: number; created: boolean }>(
        `${API_BASE}/storyboards/draft`,
        { title: trimmed, group_id: groupId },
        { timeout: API_TIMEOUT.DEFAULT }
      );
      const storyboardId = res.data.storyboard_id;
      router.push(`/studio?id=${storyboardId}&topic=${encodeURIComponent(trimmed)}`);
    } catch {
      showToast("영상 생성에 실패했습니다", "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  const summary =
    totalCount === null
      ? ""
      : totalCount === 0
        ? "Create your first story to get started"
        : `${totalCount} storyboard${totalCount !== 1 ? "s" : ""} in progress`;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-zinc-900">{getGreeting()}</h1>
          {summary && <p className="mt-0.5 text-sm text-zinc-500">{summary}</p>}
        </div>
        <Button variant="primary" size="md" onClick={() => router.push("/studio?new=true")}>
          <Plus className="h-4 w-4" />새 영상
        </Button>
      </div>

      {canQuickStart && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleQuickStart();
          }}
          className="flex items-center gap-2"
        >
          <div className="relative flex-1">
            <Sparkles className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="어떤 영상을 만들까요?"
              maxLength={200}
              disabled={isSubmitting}
              className="h-10 w-full rounded-lg border border-zinc-200 bg-white pr-3 pl-9 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none disabled:opacity-50"
            />
          </div>
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={isSubmitting || !topic.trim()}
          >
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "시작"}
          </Button>
        </form>
      )}
    </div>
  );
}
