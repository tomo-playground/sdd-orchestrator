"use client";

import { useState, useCallback, useEffect } from "react";
import axios from "axios";
import { Play, Loader2, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { API_BASE } from "../../../constants";

// ── Types ──────────────────────────────────────────────────────

type Character = {
  id: number;
  name: string;
};

type WD14Result = {
  matched_tags: string[];
  missing_tags: string[];
  extra_tags: string[];
};

type ExperimentResult = {
  id: number;
  experiment_type: string;
  status: string;
  prompt_used: string;
  target_tags: string[];
  image_url: string | null;
  match_rate: number | null;
  wd14_result: WD14Result | null;
  seed: number | null;
  created_at: string | null;
};

type HistoryItem = {
  id: number;
  target_tags: string[];
  match_rate: number | null;
  status: string;
  created_at: string | null;
};

// ── Helpers ────────────────────────────────────────────────────

function matchRateBadge(rate: number) {
  if (rate > 0.8) return { label: "HIGH", bg: "bg-emerald-50", text: "text-emerald-700" };
  if (rate > 0.5) return { label: "MED", bg: "bg-amber-50", text: "text-amber-700" };
  return { label: "LOW", bg: "bg-rose-50", text: "text-rose-700" };
}

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Component ──────────────────────────────────────────────────

export default function TagLabTab() {
  // Form state
  const [tags, setTags] = useState("");
  const [characterId, setCharacterId] = useState<number | null>(null);
  const [steps, setSteps] = useState(28);
  const [cfgScale, setCfgScale] = useState(7);
  const [seed, setSeed] = useState(-1);
  const [negativePrompt, setNegativePrompt] = useState("");

  // Data state
  const [characters, setCharacters] = useState<Character[]>([]);
  const [result, setResult] = useState<ExperimentResult | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ── Fetch characters on mount ──────────────────────────────
  useEffect(() => {
    axios
      .get<Character[]>(`${API_BASE}/characters`)
      .then((res) => setCharacters(res.data))
      .catch(() => setCharacters([]));
  }, []);

  // ── Fetch history on mount ─────────────────────────────────
  const loadHistory = useCallback(async () => {
    try {
      const res = await axios.get<{ items: HistoryItem[] }>(`${API_BASE}/lab/experiments`, {
        params: { experiment_type: "tag_render" },
      });
      setHistory(res.data.items);
    } catch {
      /* history is non-critical */
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // ── Run experiment ─────────────────────────────────────────
  const handleRun = useCallback(async () => {
    const tagList = tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    if (tagList.length === 0) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await axios.post<ExperimentResult>(`${API_BASE}/lab/experiments/run`, {
        experiment_type: "tag_render",
        character_id: characterId,
        target_tags: tagList,
        negative_prompt: negativePrompt || undefined,
        sd_params: { steps, cfg_scale: cfgScale },
        seed: seed >= 0 ? seed : undefined,
      });
      setResult(res.data);
      loadHistory();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(axiosErr.response?.data?.detail || axiosErr.message || "Experiment failed");
    } finally {
      setLoading(false);
    }
  }, [tags, characterId, negativePrompt, steps, cfgScale, seed, loadHistory]);

  // ── Render ─────────────────────────────────────────────────
  const wd14 = result?.wd14_result;

  return (
    <div className="space-y-6">
      {/* ── Top: Two-column form + result ── */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left: Form */}
        <div className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-zinc-800">Tag Experiment</h3>

          <Field label="Tags (comma-separated)">
            <textarea
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              rows={3}
              placeholder="1girl, blue_hair, school_uniform, smile"
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
            />
          </Field>

          <Field label="Character">
            <select
              value={characterId ?? ""}
              onChange={(e) => setCharacterId(e.target.value ? Number(e.target.value) : null)}
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
            >
              <option value="">None</option>
              {characters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>

          <div className="grid grid-cols-3 gap-3">
            <Field label="Steps">
              <input
                type="number"
                value={steps}
                onChange={(e) => setSteps(Number(e.target.value))}
                min={1}
                max={150}
                className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
              />
            </Field>
            <Field label="CFG Scale">
              <input
                type="number"
                value={cfgScale}
                onChange={(e) => setCfgScale(Number(e.target.value))}
                min={1}
                max={30}
                step={0.5}
                className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
              />
            </Field>
            <Field label="Seed">
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                min={-1}
                className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
              />
            </Field>
          </div>

          <Field label="Negative Prompt">
            <input
              type="text"
              value={negativePrompt}
              onChange={(e) => setNegativePrompt(e.target.value)}
              placeholder="lowres, bad anatomy, blurry"
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
            />
          </Field>

          <button
            onClick={handleRun}
            disabled={loading || !tags.trim()}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            {loading ? "Running..." : "Run Experiment"}
          </button>

          {error && (
            <p className="rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-600">{error}</p>
          )}
        </div>

        {/* Right: Result */}
        <div className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-zinc-800">Result</h3>

          {!result && !loading && (
            <p className="py-12 text-center text-xs text-zinc-400">
              Run an experiment to see results here.
            </p>
          )}

          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
            </div>
          )}

          {result && (
            <>
              {/* Image */}
              {result.image_url && (
                <div className="overflow-hidden rounded-xl border border-zinc-100">
                  <img
                    src={result.image_url}
                    alt="Generated"
                    className="h-auto w-full object-contain"
                  />
                </div>
              )}

              {/* Match rate badge */}
              {result.match_rate != null && (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-zinc-600">Match Rate:</span>
                  <MatchBadge rate={result.match_rate} />
                </div>
              )}

              {/* WD14 detail */}
              {wd14 && (
                <div className="space-y-2">
                  <TagList
                    icon={<CheckCircle className="h-3 w-3 text-emerald-500" />}
                    label="Matched"
                    tags={wd14.matched_tags}
                    color="text-emerald-700"
                  />
                  <TagList
                    icon={<XCircle className="h-3 w-3 text-rose-500" />}
                    label="Missing"
                    tags={wd14.missing_tags}
                    color="text-rose-700"
                  />
                  <TagList
                    icon={<AlertTriangle className="h-3 w-3 text-amber-500" />}
                    label="Extra"
                    tags={wd14.extra_tags}
                    color="text-amber-700"
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* ── Bottom: History ── */}
      <div className="rounded-2xl border border-zinc-200 bg-white p-5">
        <h3 className="mb-3 text-sm font-semibold text-zinc-800">Experiment History</h3>

        {history.length === 0 ? (
          <p className="py-4 text-center text-xs text-zinc-400">No experiments yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-100 text-left text-[10px] font-semibold tracking-wider text-zinc-400 uppercase">
                  <th className="pr-4 pb-2">ID</th>
                  <th className="pr-4 pb-2">Tags</th>
                  <th className="pr-4 pb-2">Match Rate</th>
                  <th className="pr-4 pb-2">Status</th>
                  <th className="pb-2">Date</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id} className="border-b border-zinc-50 text-zinc-600">
                    <td className="py-2 pr-4 font-mono text-zinc-400">#{item.id}</td>
                    <td className="max-w-[200px] truncate py-2 pr-4">
                      {item.target_tags.join(", ")}
                    </td>
                    <td className="py-2 pr-4">
                      {item.match_rate != null ? <MatchBadge rate={item.match_rate} /> : "-"}
                    </td>
                    <td className="py-2 pr-4">{item.status}</td>
                    <td className="py-2 text-zinc-400">{formatDate(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] font-semibold tracking-wider text-zinc-500 uppercase">
        {label}
      </span>
      {children}
    </label>
  );
}

function MatchBadge({ rate }: { rate: number }) {
  const badge = matchRateBadge(rate);
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${badge.bg} ${badge.text}`}
    >
      {badge.label} {(rate * 100).toFixed(0)}%
    </span>
  );
}

function TagList({
  icon,
  label,
  tags,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  tags: string[];
  color: string;
}) {
  if (tags.length === 0) return null;
  return (
    <div>
      <div className="mb-1 flex items-center gap-1 text-[10px] font-semibold text-zinc-500">
        {icon}
        {label} ({tags.length})
      </div>
      <div className="flex flex-wrap gap-1">
        {tags.map((tag) => (
          <span key={tag} className={`rounded bg-zinc-50 px-1.5 py-0.5 text-[10px] ${color}`}>
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}
