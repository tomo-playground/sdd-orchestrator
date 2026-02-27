"use client";

import { ArrowRight, CheckCircle2 } from "lucide-react";
import Button from "../ui/Button";

type CategoryStatus = {
  key: string;
  label: string;
  ready: boolean;
};

type Props = {
  categories: CategoryStatus[];
  isAssigning: boolean;
  onContinue: () => void;
};

export default function StageReadinessBar({ categories, isAssigning, onContinue }: Props) {
  const readyCount = categories.filter((c) => c.ready).length;
  const allReady = readyCount === categories.length && categories.length > 0;

  return (
    <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
      {/* Progress header */}
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium text-zinc-600">
          Pre-production: {readyCount}/{categories.length} ready
        </span>
        {allReady && (
          <span className="flex items-center gap-1 text-xs font-medium text-emerald-600">
            <CheckCircle2 className="h-3.5 w-3.5" />
            All Ready
          </span>
        )}
      </div>

      {/* Segmented progress bar */}
      <div className="flex gap-1">
        {categories.map((cat) => (
          <div key={cat.key} className="flex-1">
            <div
              className={`h-2 rounded-full transition-colors ${
                cat.ready ? "bg-emerald-500" : "bg-zinc-200"
              }`}
            />
          </div>
        ))}
      </div>

      {/* Category chips */}
      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {categories.map((cat) => (
          <span
            key={cat.key}
            className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
              cat.ready ? "bg-emerald-100 text-emerald-700" : "bg-zinc-100 text-zinc-400"
            }`}
          >
            {cat.label}
          </span>
        ))}
      </div>

      {/* Continue button */}
      {allReady && (
        <div className="mt-3 flex justify-end">
          <Button size="sm" onClick={onContinue} loading={isAssigning} disabled={isAssigning}>
            Continue to Direct
            <ArrowRight className="ml-1 h-3.5 w-3.5" />
          </Button>
        </div>
      )}
    </div>
  );
}
