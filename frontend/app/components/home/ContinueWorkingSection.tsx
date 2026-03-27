"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Clock, Loader2 } from "lucide-react";
import { formatRelativeTime } from "../../utils/format";
import { API_BASE } from "../../constants";

type RecentStoryboard = {
  id: number;
  title: string;
  scene_count: number;
  image_count: number;
  kanban_status: "draft" | "in_prod" | "rendered" | "published";
  stage_status: string | null;
  updated_at: string | null;
};

const STEPS = ["script", "stage", "images", "render", "done"] as const;
type ProgressStep = (typeof STEPS)[number];

const STEP_META: Record<ProgressStep, { label: string; color: string }> = {
  script: { label: "스크립트", color: "bg-zinc-400" },
  stage: { label: "스테이지", color: "bg-amber-400" },
  images: { label: "이미지", color: "bg-blue-400" },
  render: { label: "렌더", color: "bg-violet-400" },
  done: { label: "완료", color: "bg-emerald-400" },
};

/** kanban_status + stage_status + image_count 조합으로 5단계 파생 */
export function deriveProgressStep(sb: RecentStoryboard): ProgressStep {
  if (sb.kanban_status === "published") return "done";
  if (sb.kanban_status === "rendered") return "render";
  if (sb.kanban_status === "in_prod" && sb.image_count > 0) return "images";
  if (
    sb.stage_status === "staged" ||
    sb.stage_status === "staging" ||
    sb.stage_status === "failed"
  )
    return "stage";
  return "script";
}

export default function ContinueWorkingSection() {
  const router = useRouter();
  const [items, setItems] = useState<RecentStoryboard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchRecent() {
      try {
        const res = await fetch(`${API_BASE}/storyboards?limit=3`);
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
        <h2 className="text-sm font-semibold text-zinc-900">이어서 작업</h2>
      </div>

      <div className="-mx-1 flex gap-3 overflow-x-auto px-1 pb-2">
        {items.map((sb) => {
          const progress =
            sb.scene_count > 0 ? Math.round((sb.image_count / sb.scene_count) * 100) : 0;
          const currentStep = deriveProgressStep(sb);
          const currentIdx = STEPS.indexOf(currentStep);

          return (
            <button
              key={sb.id}
              onClick={() => router.push(`/studio?id=${sb.id}`)}
              className="group w-[220px] shrink-0 rounded-xl border border-zinc-200 bg-white p-3 text-left transition hover:border-zinc-300 hover:shadow-sm"
            >
              <p className="truncate text-sm font-medium text-zinc-900">{sb.title || "Untitled"}</p>

              {/* Step dots + label */}
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

              {/* Progress bar + count + time */}
              <div className="mt-2 flex items-center gap-2">
                {sb.scene_count > 0 ? (
                  <>
                    <div className="h-1 flex-1 rounded-full bg-zinc-100">
                      <div
                        className="h-1 rounded-full bg-zinc-400 transition-all"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <span className="text-[11px] text-zinc-400">
                      {sb.image_count}/{sb.scene_count}
                    </span>
                  </>
                ) : (
                  <div className="flex-1" />
                )}
                {sb.updated_at && (
                  <span className="shrink-0 text-[11px] text-zinc-400">
                    {formatRelativeTime(sb.updated_at)}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
