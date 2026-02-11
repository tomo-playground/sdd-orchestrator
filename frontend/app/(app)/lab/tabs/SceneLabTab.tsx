"use client";

import { useState, useCallback, useEffect } from "react";
import axios from "axios";
import { Play, Loader2, CheckCircle, XCircle, AlertTriangle, ArrowRight } from "lucide-react";
import { API_BASE } from "../../../constants";

// -- Types -------------------------------------------------------------------

type Character = {
  id: number;
  name: string;
  project_id: number;
};

type Group = {
  id: number;
  name: string;
  project_id: number;
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
  scene_description: string | null;
  seed: number | null;
  created_at: string | null;
};

type HistoryItem = {
  id: number;
  scene_description: string | null;
  target_tags: string[];
  match_rate: number | null;
  status: string;
  created_at: string | null;
};

// -- Helpers -----------------------------------------------------------------

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

// -- Component ---------------------------------------------------------------

export default function SceneLabTab() {
  // Form state
  const [sceneDescription, setSceneDescription] = useState("");
  const [characterId, setCharacterId] = useState<number | null>(null);
  const [groupId, setGroupId] = useState<number | null>(null);
  const [steps, setSteps] = useState(28);
  const [cfgScale, setCfgScale] = useState(7);
  const [seed, setSeed] = useState(-1);
  const [negativePrompt, setNegativePrompt] = useState("");

  // Data state
  const [characters, setCharacters] = useState<Character[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [result, setResult] = useState<ExperimentResult | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Fetch characters and groups on mount
  useEffect(() => {
    axios
      .get<Character[]>(`${API_BASE}/characters`)
      .then((res) => setCharacters(res.data))
      .catch(() => setCharacters([]));

    axios
      .get<Group[]>(`${API_BASE}/groups`)
      .then((res) => {
        setGroups(res.data);
        if (res.data.length > 0) {
          setGroupId(res.data[0].id);
        }
      })
      .catch(() => setGroups([]));
  }, []);

  // Filter groups when character changes
  const availableGroups = characterId
    ? groups.filter((g) => {
        const char = characters.find((c) => c.id === characterId);
        return char ? g.project_id === char.project_id : true;
      })
    : groups;

  // Update groupId when character changes and current group is invalid
  useEffect(() => {
    if (characterId && groupId) {
      const isValidGroup = availableGroups.some((g) => g.id === groupId);
      if (!isValidGroup && availableGroups.length > 0) {
        setGroupId(availableGroups[0].id);
      }
    }
  }, [characterId, groupId, availableGroups]);

  // Fetch history on mount
  const loadHistory = useCallback(async () => {
    try {
      const res = await axios.get<{ items: HistoryItem[] }>(`${API_BASE}/lab/experiments`, {
        params: { experiment_type: "scene_translate" },
      });
      setHistory(res.data.items);
    } catch {
      /* history is non-critical */
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Run compose-and-run
  const handleRun = useCallback(async () => {
    if (!sceneDescription.trim() || !characterId || !groupId) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await axios.post<ExperimentResult>(
        `${API_BASE}/lab/experiments/compose-and-run`,
        {
          experiment_type: "scene_translate",
          scene_description: sceneDescription,
          group_id: groupId,
          character_id: characterId,
          negative_prompt: negativePrompt || undefined,
          sd_params: { steps, cfg_scale: cfgScale },
          seed: seed >= 0 ? seed : undefined,
          target_tags: [],
        }
      );
      setResult(res.data);
      loadHistory();
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      setError(axiosErr.response?.data?.detail || axiosErr.message || "Experiment failed");
    } finally {
      setLoading(false);
    }
  }, [sceneDescription, groupId, characterId, negativePrompt, steps, cfgScale, seed, loadHistory]);

  const wd14 = result?.wd14_result;

  return (
    <div className="space-y-6">
      {/* ── Purpose Section ── */}
      <div className="rounded-2xl border border-purple-100 bg-gradient-to-br from-purple-50 to-white p-5">
        <h2 className="mb-2 text-base font-bold text-zinc-800">Scene Lab</h2>
        <p className="text-xs leading-relaxed text-zinc-600">
          <strong className="text-zinc-700">목표:</strong> Gemini가 생성한 한글 씬 설명이 영문
          태그로 올바르게 변환되는지 검증합니다.
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-zinc-500">
          한글 프롬프트 → 영문 태그 변환 파이프라인의 정확성을 테스트합니다. 씬 설명에서 핵심
          요소(캐릭터, 배경, 감정 등)가 누락 없이 태그로 변환되는지 확인합니다.
        </p>

        {/* Collapsible Details */}
        <details className="mt-3">
          <summary className="cursor-pointer text-xs font-semibold text-purple-700 hover:text-purple-800">
            📖 자세히 보기
          </summary>
          <div className="mt-3 space-y-3 rounded-lg border border-purple-100 bg-white p-3 text-xs">
            <div>
              <strong className="text-zinc-700">💡 사용 시나리오:</strong>
              <ul className="mt-1 ml-4 list-disc space-y-0.5 text-zinc-600">
                <li>Gemini 프롬프트 템플릿 수정 후 변환 품질 확인</li>
                <li>새로운 감정/배경 표현 추가 시 태그 변환 테스트</li>
                <li>한글 → 영문 변환 누락 요소 발견 및 개선</li>
              </ul>
            </div>
            <div>
              <strong className="text-zinc-700">✅ 성공 기준:</strong>
              <span className="ml-1 text-zinc-600">
                핵심 요소(캐릭터, 배경, 감정){" "}
                <strong className="text-emerald-600">모두 태그 변환</strong>
              </span>
            </div>
            <div>
              <strong className="text-zinc-700">📊 주요 메트릭:</strong>
              <span className="ml-1 text-zinc-600">Translation Accuracy, Missing Elements</span>
            </div>
            <div>
              <strong className="text-zinc-700">🔄 워크플로우:</strong>
              <span className="ml-1 text-zinc-600">
                Scene Lab → 프롬프트 템플릿 개선 → Studio 자동화 향상
              </span>
            </div>
            <div>
              <strong className="text-zinc-700">⚡ Quick Tips:</strong>
              <ul className="mt-1 ml-4 list-disc space-y-0.5 text-zinc-600">
                <li>Character 선택 시 LoRA 자동 적용</li>
                <li>한글 묘사를 구체적으로 작성할수록 정확도 향상</li>
              </ul>
            </div>
          </div>
        </details>
      </div>

      {/* Top: Two-column form + result */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left: Form */}
        <div className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-zinc-800">Scene Translation</h3>

          <Field label="Scene Description">
            <textarea
              value={sceneDescription}
              onChange={(e) => setSceneDescription(e.target.value)}
              rows={3}
              placeholder="cowboy_shot, smile, looking_at_viewer, cafe, sitting"
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none"
            />
          </Field>

          <Field label="Character (required)">
            <select
              value={characterId ?? ""}
              onChange={(e) => setCharacterId(e.target.value ? Number(e.target.value) : null)}
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
            >
              <option value="">Select a character</option>
              {characters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Group (Style Profile)">
            <select
              value={groupId ?? ""}
              onChange={(e) => setGroupId(e.target.value ? Number(e.target.value) : null)}
              className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 focus:border-zinc-400 focus:outline-none"
              title="Group determines which Style Profile (LoRAs, Quality Tags) to use"
            >
              {availableGroups.length === 0 ? (
                <option value="">No groups available</option>
              ) : (
                availableGroups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))
              )}
            </select>
            <p className="mt-1 text-[12px] text-zinc-400">
              Applies Style Profile (LoRAs + Quality Tags) from this Group
            </p>
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
            disabled={loading || !sceneDescription.trim() || !characterId || !groupId}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            {loading ? "Composing & Generating..." : "Compose & Run"}
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
              Compose and run an experiment to see results here.
            </p>
          )}

          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
            </div>
          )}

          {result && (
            <>
              {/* Process visualization */}
              <ProcessVisualization
                description={result.scene_description}
                composedPrompt={result.prompt_used}
              />

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

      {/* Bottom: History */}
      <div className="rounded-2xl border border-zinc-200 bg-white p-5">
        <h3 className="mb-3 text-sm font-semibold text-zinc-800">Scene Translation History</h3>

        {history.length === 0 ? (
          <p className="py-4 text-center text-xs text-zinc-400">
            No scene translation experiments yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-100 text-left text-[12px] font-semibold tracking-wider text-zinc-400 uppercase">
                  <th className="pr-4 pb-2">ID</th>
                  <th className="pr-4 pb-2">Description</th>
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
                      {item.scene_description || item.target_tags.join(", ")}
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

// -- Sub-components ----------------------------------------------------------

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] font-semibold tracking-wider text-zinc-500 uppercase">
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
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[12px] font-bold ${badge.bg} ${badge.text}`}
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
      <div className="mb-1 flex items-center gap-1 text-[12px] font-semibold text-zinc-500">
        {icon}
        {label} ({tags.length})
      </div>
      <div className="flex flex-wrap gap-1">
        {tags.map((tag) => (
          <span key={tag} className={`rounded bg-zinc-50 px-1.5 py-0.5 text-[12px] ${color}`}>
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}

function ProcessVisualization({
  description,
  composedPrompt,
}: {
  description: string | null;
  composedPrompt: string;
}) {
  if (!description) return null;
  return (
    <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-3">
      <div className="mb-2 text-[12px] font-semibold tracking-wider text-zinc-400 uppercase">
        Translation Pipeline
      </div>
      <div className="space-y-2">
        <div>
          <span className="text-[12px] font-medium text-zinc-500">Input:</span>
          <p className="mt-0.5 text-xs text-zinc-700">{description}</p>
        </div>
        <div className="flex justify-center">
          <ArrowRight className="h-3 w-3 text-zinc-300" />
        </div>
        <div>
          <span className="text-[12px] font-medium text-zinc-500">V3 Composed:</span>
          <p className="mt-0.5 text-xs break-all text-zinc-700">{composedPrompt}</p>
        </div>
      </div>
    </div>
  );
}
