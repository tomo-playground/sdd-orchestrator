"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Clock, Loader2 } from "lucide-react";
import { formatRelativeTime } from "../../utils/format";

type RecentStoryboard = {
  id: number;
  title: string;
  scene_count: number;
  image_count: number;
  kanban_status: "draft" | "in_prod" | "rendered" | "published";
  updated_at: string | null;
};

const STEP_META: Record<string, { label: string; color: string }> = {
  draft: { label: "Script", color: "bg-zinc-400" },
  in_prod: { label: "Edit", color: "bg-amber-400" },
  rendered: { label: "Publish", color: "bg-blue-400" },
  published: { label: "Done", color: "bg-emerald-400" },
};

const STEPS = ["draft", "in_prod", "rendered", "published"] as const;

export default function ContinueWorkingSection() {
  const router = useRouter();
  const [items, setItems] = useState<RecentStoryboard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchRecent() {
      try {
        const res = await fetch(`/api/storyboards?limit=3`);
        if (!res.ok) throw new Error("fetch failed");
        const data = await res.json();
        setItems(data.items ?? []);
      } catch {
        setItems([]);
      } finally {
        setLoading(false);
      }
    }
    fetchRecent();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-zinc-200 bg-white p-8">
        <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (items.length === 0) return null;

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <Clock className="h-4 w-4 text-zinc-500" />
        <h2 className="text-sm font-semibold text-zinc-900">Continue Working</h2>
      </div>

      <div className="space-y-2">
        {items.map((sb) => {
          const progress =
            sb.scene_count > 0 ? Math.round((sb.image_count / sb.scene_count) * 100) : 0;
          const currentStep = sb.kanban_status;
          const currentIdx = STEPS.indexOf(currentStep);

          return (
            <button
              key={sb.id}
              onClick={() => router.push(`/studio?id=${sb.id}`)}
              className="group flex w-full items-center gap-4 rounded-xl border border-zinc-200 bg-white p-4 text-left transition hover:border-zinc-300 hover:shadow-sm"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-zinc-900">
                  {sb.title || "Untitled"}
                </p>

                {/* Step dots */}
                <div className="mt-2 flex items-center gap-1.5">
                  {STEPS.map((step, i) => (
                    <div key={step} className="flex items-center gap-1.5">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          i <= currentIdx ? STEP_META[step].color : "bg-zinc-200"
                        }`}
                        title={STEP_META[step].label}
                      />
                      {i < STEPS.length - 1 && (
                        <div
                          className={`h-px w-3 ${i < currentIdx ? "bg-zinc-300" : "bg-zinc-100"}`}
                        />
                      )}
                    </div>
                  ))}
                  <span className="ml-2 text-[11px] text-zinc-400">
                    {STEP_META[currentStep].label}
                  </span>
                </div>

                {/* Progress bar */}
                {sb.scene_count > 0 && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="h-1 flex-1 rounded-full bg-zinc-100">
                      <div
                        className="h-1 rounded-full bg-zinc-400 transition-all"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <span className="text-[11px] text-zinc-400">
                      {sb.image_count}/{sb.scene_count}
                    </span>
                  </div>
                )}
              </div>

              <div className="flex shrink-0 flex-col items-end gap-1">
                {sb.updated_at && (
                  <span className="text-[11px] text-zinc-400">
                    {formatRelativeTime(sb.updated_at)}
                  </span>
                )}
                <ArrowRight className="h-4 w-4 text-zinc-300 transition group-hover:text-zinc-600" />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
