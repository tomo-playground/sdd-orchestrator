"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";
import { useCharacters } from "../../../hooks";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import type { Character } from "../../../types";

type EvaluationTest = {
  name: string;
  description: string;
  tokens: string[];
};

type EvaluationResultTest = {
  test_name: string;
  description?: string;
  standard_avg: number;
  lora_avg: number;
  winner: "standard" | "lora" | "tie";
  diff: number;
};

type EvaluationSummary = {
  overall: {
    standard_avg: number;
    lora_avg: number;
    winner: "standard" | "lora" | "tie";
    diff: number;
  };
  tests: EvaluationResultTest[];
};

const TEST_PROMPTS: EvaluationTest[] = [
  {
    name: "consistency_check",
    description: "Evaluates character identity preservation across angles",
    tokens: ["face", "identity", "consistent", "multiview"],
  },
  {
    name: "style_adherence",
    description: "Checks if the generated style matches the reference",
    tokens: ["style", "color", "stroke", "texture"],
  },
  {
    name: "anatomy_quality",
    description: "Detects anatomical errors (hands, limbs)",
    tokens: ["anatomy", "hands", "limbs", "structure"],
  },
  {
    name: "prompt_following",
    description: "Measures how well the image follows text instructions",
    tokens: ["instruction", "elements", "composition"],
  },
];

export default function EvaluationTab() {
  const { characters } = useCharacters();

  const [evalCharacterId, setEvalCharacterId] = useState<number | null>(null);
  const [evalRepetitions, setEvalRepetitions] = useState(2);
  const [selectedTests, setSelectedTests] = useState<Set<string>>(new Set());
  const [isEvalRunning, setIsEvalRunning] = useState(false);
  const [isEvalLoading, setIsEvalLoading] = useState(false);
  const [evalSummary, setEvalSummary] = useState<EvaluationSummary | null>(null);
  const [evalLastBatchId] = useState<string | null>(null);

  useEffect(() => {
    void fetchEvalData();
  }, []);

  const fetchEvalData = async () => {
    setIsEvalLoading(true);
    try {
      const res = await axios.get<EvaluationSummary>(`${API_BASE}/eval/summary`);
      setEvalSummary(res.data || null);
      // batch_id is not returned by summary endpoint currently
      // if (res.data.batch_id) setEvalLastBatchId(res.data.batch_id);
    } catch {
      console.error("Failed to fetch evaluation data");
    } finally {
      setIsEvalLoading(false);
    }
  };

  const runEvaluation = async () => {
    if (selectedTests.size === 0) return;
    setIsEvalRunning(true);
    try {
      const payload = {
        character_id: evalCharacterId,
        repetitions: evalRepetitions,
        tests: Array.from(selectedTests),
      };
      await axios.post(`${API_BASE}/eval/run`, payload);
      // Poll for results or just wait? For now, simple wait then refresh.
      // In a real scenario, we might want a polling mechanism or websocket.
      // Assuming the backend is synchronous or fast enough, or we just refresh.
      // Actually ManagePage just awaits it.
      await fetchEvalData();
    } catch {
      alert("Evaluation failed to start");
    } finally {
      setIsEvalRunning(false);
    }
  };

  return (
    <section className="grid gap-6 rounded-2xl border border-zinc-200/60 bg-white p-6 text-xs text-zinc-600 shadow-sm">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={evalCharacterId ?? ""}
          onChange={(e) => setEvalCharacterId(e.target.value ? Number(e.target.value) : null)}
          className="rounded-full border border-zinc-200 bg-white px-3 py-2 text-xs outline-none focus:border-indigo-300"
        >
          <option value="">All Characters</option>
          {characters.map((c: Character) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-zinc-500">Reps:</span>
          <input
            type="number"
            value={evalRepetitions}
            onChange={(e) => setEvalRepetitions(Math.max(1, Math.min(10, Number(e.target.value))))}
            min={1}
            max={10}
            className="w-12 rounded border border-zinc-200 px-2 py-1 text-center text-xs outline-none focus:border-indigo-300"
          />
        </div>
        <button
          type="button"
          onClick={runEvaluation}
          disabled={isEvalRunning || selectedTests.size === 0}
          className="rounded-full bg-indigo-600 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-white uppercase transition hover:bg-indigo-700 disabled:bg-indigo-300"
        >
          {isEvalRunning ? (
            <span className="flex items-center gap-2">
              <LoadingSpinner size="sm" color="text-white" />
              Running...
            </span>
          ) : (
            `Run (${selectedTests.size})`
          )}
        </button>
        <button
          type="button"
          onClick={fetchEvalData}
          disabled={isEvalLoading}
          className="rounded-full border border-zinc-200 bg-white px-3 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase hover:bg-zinc-50"
        >
          Refresh
        </button>
      </div>

      {/* Test Selection */}
      <div className="grid gap-3">
        <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Test Prompts
        </span>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {TEST_PROMPTS.map((test) => (
            <label
              key={test.name}
              className={`flex cursor-pointer items-start gap-2 rounded-xl border p-3 transition ${
                selectedTests.has(test.name)
                  ? "border-indigo-300 bg-indigo-50"
                  : "border-zinc-200 bg-white hover:border-zinc-300"
              }`}
            >
              <input
                type="checkbox"
                checked={selectedTests.has(test.name)}
                onChange={(e) => {
                  const newSet = new Set(selectedTests);
                  if (e.target.checked) newSet.add(test.name);
                  else newSet.delete(test.name);
                  setSelectedTests(newSet);
                }}
                className="mt-0.5 rounded border-zinc-300"
              />
              <div className="flex-1">
                <div className="text-xs font-medium text-zinc-800">
                  {test.name.replace(/_/g, " ")}
                </div>
                <div className="text-[10px] text-zinc-500">{test.description}</div>
                <div className="mt-1 flex flex-wrap gap-1">
                  {test.tokens.slice(0, 4).map((t) => (
                    <span
                      key={t}
                      className="rounded bg-zinc-100 px-1.5 py-0.5 text-[9px] text-zinc-600"
                    >
                      {t}
                    </span>
                  ))}
                  {test.tokens.length > 4 && (
                    <span className="text-[9px] text-zinc-400">+{test.tokens.length - 4}</span>
                  )}
                </div>
              </div>
            </label>
          ))}
        </div>
        {TEST_PROMPTS.length > 0 && (
          <button
            type="button"
            onClick={() => {
              if (selectedTests.size === TEST_PROMPTS.length) {
                setSelectedTests(new Set());
              } else {
                setSelectedTests(new Set(TEST_PROMPTS.map((t) => t.name)));
              }
            }}
            className="w-fit text-[10px] text-indigo-600 hover:underline"
          >
            {selectedTests.size === TEST_PROMPTS.length ? "Deselect All" : "Select All"}
          </button>
        )}
      </div>

      {/* Results Summary */}
      {evalSummary && evalSummary.tests.length > 0 && (
        <div className="grid gap-3">
          <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Results Summary
          </span>

          {/* Overall Stats */}
          <div className="rounded-2xl border border-zinc-200 bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-800">Overall</span>
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                  evalSummary.overall.winner === "lora"
                    ? "bg-emerald-100 text-emerald-700"
                    : evalSummary.overall.winner === "standard"
                      ? "bg-blue-100 text-blue-700"
                      : "bg-zinc-100 text-zinc-600"
                }`}
              >
                {evalSummary.overall.winner === "tie"
                  ? "Tie"
                  : `${evalSummary.overall.winner.toUpperCase()} +${Math.abs(evalSummary.overall.diff * 100).toFixed(1)}%`}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl bg-blue-50 p-3 text-center">
                <div className="text-[10px] font-semibold tracking-[0.2em] text-blue-600 uppercase">
                  Standard
                </div>
                <div className="text-lg font-bold text-blue-700">
                  {(evalSummary.overall.standard_avg * 100).toFixed(1)}%
                </div>
              </div>
              <div className="rounded-xl bg-emerald-50 p-3 text-center">
                <div className="text-[10px] font-semibold tracking-[0.2em] text-emerald-600 uppercase">
                  LoRA
                </div>
                <div className="text-lg font-bold text-emerald-700">
                  {(evalSummary.overall.lora_avg * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          {/* Per-Test Results */}
          <div className="grid gap-2">
            {evalSummary.tests.map((test) => (
              <div
                key={test.test_name}
                className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-4 py-3"
              >
                <span className="text-xs font-medium text-zinc-700">
                  {test.test_name.replace(/_/g, " ")}
                </span>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-[10px] text-blue-600">STD</span>
                    <span className="ml-1 text-xs font-semibold text-zinc-700">
                      {test.standard_avg !== undefined
                        ? `${(test.standard_avg * 100).toFixed(1)}%`
                        : "-"}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-emerald-600">LoRA</span>
                    <span className="ml-1 text-xs font-semibold text-zinc-700">
                      {test.lora_avg !== undefined ? `${(test.lora_avg * 100).toFixed(1)}%` : "-"}
                    </span>
                  </div>
                  <span
                    className={`w-16 rounded-full px-2 py-0.5 text-center text-[10px] font-semibold ${
                      test.winner === "lora"
                        ? "bg-emerald-100 text-emerald-700"
                        : test.winner === "standard"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-zinc-100 text-zinc-500"
                    }`}
                  >
                    {test.winner === "tie" ? "Tie" : test.winner.toUpperCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {evalLastBatchId && (
            <div className="text-[10px] text-zinc-400">Last batch: {evalLastBatchId}</div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!isEvalLoading && (!evalSummary || evalSummary.tests.length === 0) && (
        <div className="rounded-2xl border border-dashed border-zinc-300 bg-zinc-50 p-8 text-center">
          <div className="text-sm text-zinc-500">No evaluation data yet</div>
          <div className="mt-1 text-[10px] text-zinc-400">
            Select tests above and click Run to compare Mode A vs B
          </div>
        </div>
      )}
    </section>
  );
}
