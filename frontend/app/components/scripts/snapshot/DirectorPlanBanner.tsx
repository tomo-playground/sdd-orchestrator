"use client";

import { Target } from "lucide-react";
import type { ProductionSnapshot } from "../../../types";

type Props = {
  plan: NonNullable<ProductionSnapshot["director_plan"]>;
};

export default function DirectorPlanBanner({ plan }: Props) {
  const goal = plan.creative_goal;
  const emotion = plan.target_emotion;

  if (!goal && !emotion) return null;

  return (
    <div className="mb-3 flex items-start gap-2 rounded-lg bg-indigo-50 px-3 py-2">
      <Target className="mt-0.5 h-3.5 w-3.5 shrink-0 text-indigo-500" />
      <p className="text-xs leading-relaxed text-indigo-700">
        {goal && <span className="font-medium">{goal}</span>}
        {goal && emotion && <span className="mx-1 text-indigo-400">·</span>}
        {emotion && <span>{emotion}</span>}
      </p>
    </div>
  );
}
