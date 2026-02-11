"use client";

import { useState } from "react";
import type { PipelineLog } from "../../types/creative";

type Props = {
  logs: PipelineLog[];
  stepKey: string;
  isRunning: boolean;
};

export default function StepLogs({ logs, stepKey, isRunning }: Props) {
  const [manualOpen, setManualOpen] = useState(false);
  const filtered = logs.filter((l) => l.step === stepKey);
  const open = isRunning || manualOpen;

  if (filtered.length === 0) return null;

  return (
    <div className="mt-2">
      <button
        onClick={() => setManualOpen(!manualOpen)}
        className="text-[10px] text-zinc-400 hover:text-zinc-600"
      >
        {open ? "\u25BE" : "\u25B8"} Logs ({filtered.length})
      </button>
      {open && (
        <div className="mt-1 max-h-24 overflow-y-auto rounded bg-zinc-900 p-2 font-mono text-[10px] text-zinc-300">
          {filtered.map((log, i) => (
            <div key={i} className={log.level === "error" ? "text-red-400" : ""}>
              <span className="text-zinc-500">{new Date(log.ts).toLocaleTimeString()}</span>{" "}
              {log.msg}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
