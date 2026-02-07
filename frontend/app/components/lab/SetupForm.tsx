"use client";

import { Loader2, Play } from "lucide-react";

type Props = {
  taskType: string;
  objective: string;
  maxRounds: number;
  debateLoading: boolean;
  onTaskTypeChange: (v: string) => void;
  onObjectiveChange: (v: string) => void;
  onMaxRoundsChange: (v: number) => void;
  onStartDebate: () => void;
};

export default function SetupForm({
  taskType,
  objective,
  maxRounds,
  debateLoading,
  onTaskTypeChange,
  onObjectiveChange,
  onMaxRoundsChange,
  onStartDebate,
}: Props) {
  return (
    <div className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5">
      <p className="text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
        New Creative Session
      </p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Task Type
          </label>
          <select
            value={taskType}
            onChange={(e) => onTaskTypeChange(e.target.value)}
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
          >
            <option value="scenario">Scenario</option>
            <option value="dialogue">Dialogue</option>
            <option value="visual_concept">Visual Concept</option>
            <option value="character_design">Character Design</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
            Max Rounds
          </label>
          <input
            type="number"
            min={1}
            max={10}
            value={maxRounds}
            onChange={(e) => onMaxRoundsChange(Number(e.target.value))}
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
          />
        </div>
      </div>
      <div>
        <label className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
          Objective
        </label>
        <textarea
          value={objective}
          onChange={(e) => onObjectiveChange(e.target.value)}
          rows={3}
          placeholder="Describe what you want the agents to create..."
          className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
        />
      </div>
      <div className="flex justify-end">
        <button
          onClick={onStartDebate}
          disabled={debateLoading || !objective.trim()}
          className="flex items-center gap-1.5 rounded-lg bg-zinc-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
        >
          {debateLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          Start Debate
        </button>
      </div>
    </div>
  );
}
