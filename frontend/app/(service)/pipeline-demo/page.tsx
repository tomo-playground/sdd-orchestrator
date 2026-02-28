"use client";

import { useState, useEffect, useRef, useCallback } from "react";

// ── Types ───────────────────────────────────────────────────
type AutomationLevel = "manual" | "assisted" | "delegated";

interface PipelineConfig {
  concept: AutomationLevel;
  script: AutomationLevel;
  prompts: AutomationLevel;
  images: AutomationLevel;
  render: AutomationLevel;
}

type PipelineStage =
  | "idle"
  | "researching"
  | "drafting"
  | "reviewing"
  | "waiting_approval"
  | "revising"
  | "generating_images"
  | "completed";

type NodeStatus = "pending" | "running" | "done" | "failed" | "waiting";

interface StageNode {
  id: string;
  label: string;
  status: NodeStatus;
  detail?: string;
  elapsed?: number;
  children?: { label: string; status: NodeStatus; detail?: string }[];
}

interface MockScene {
  scene_number: number;
  script: string;
  image_prompt: string;
}

// ── Mock Data ───────────────────────────────────────────────
const MOCK_SCENES: MockScene[] = [
  {
    scene_number: 1,
    script: "처음 칼을 잡았을 때, 너무 무서웠어",
    image_prompt: "1boy, sword, trembling_hands, dawn",
  },
  {
    scene_number: 2,
    script: "매일 새벽 훈련을 했다. 누구보다 열심히.",
    image_prompt: "1boy, training, sweat, morning_light",
  },
  {
    scene_number: 3,
    script: "처음으로 승리한 날, 눈물이 멈추지 않았다",
    image_prompt: "1boy, victory, tears, stadium",
  },
  {
    scene_number: 4,
    script: "진짜 강함이란, 쓰러져도 다시 일어나는 것",
    image_prompt: "1boy, standing_up, bruised, determined",
  },
  {
    scene_number: 5,
    script: "오늘도 칼을 든다. 어제보다 더 강하게.",
    image_prompt: "1boy, sword, confident, sunset",
  },
];

const PRESETS: { label: string; icon: string; config: PipelineConfig }[] = [
  {
    label: "Creator",
    icon: "direct_hit",
    config: {
      concept: "delegated",
      script: "assisted",
      prompts: "delegated",
      images: "delegated",
      render: "delegated",
    },
  },
  {
    label: "Full Auto",
    icon: "robot",
    config: {
      concept: "delegated",
      script: "delegated",
      prompts: "delegated",
      images: "delegated",
      render: "delegated",
    },
  },
  {
    label: "Manual",
    icon: "pencil",
    config: {
      concept: "manual",
      script: "manual",
      prompts: "manual",
      images: "manual",
      render: "manual",
    },
  },
];

const STAGE_STEPS: { id: string; label: string; configKey?: keyof PipelineConfig }[] = [
  { id: "research", label: "Research" },
  { id: "concept", label: "Concept", configKey: "concept" },
  { id: "script", label: "Script", configKey: "script" },
  { id: "prompts", label: "Prompts", configKey: "prompts" },
  { id: "images", label: "Images", configKey: "images" },
  { id: "finalize", label: "Finalize" },
];

// ── Helpers ─────────────────────────────────────────────────
function formatElapsed(ms: number): string {
  return (ms / 1000).toFixed(1) + "s";
}

const AUTOMATION_LABELS: Record<AutomationLevel, string> = {
  manual: "Manual",
  assisted: "Assisted",
  delegated: "Delegated",
};

const AUTOMATION_COLORS: Record<AutomationLevel, string> = {
  manual: "text-zinc-400",
  assisted: "text-amber-400",
  delegated: "text-emerald-400",
};

// ── Sub-Components ──────────────────────────────────────────

function LevelSelect({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: AutomationLevel;
  onChange: (v: AutomationLevel) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs font-medium text-zinc-300">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as AutomationLevel)}
        disabled={disabled}
        className="rounded-lg border border-zinc-600 bg-zinc-700 px-2 py-1 text-xs text-zinc-200 outline-none focus:border-zinc-400 disabled:opacity-40"
      >
        <option value="manual">Manual</option>
        <option value="assisted">Assisted</option>
        <option value="delegated">Delegated</option>
      </select>
    </div>
  );
}

function NodeIcon({ status }: { status: NodeStatus }) {
  switch (status) {
    case "done":
      return <span className="text-emerald-400">&#10003;</span>;
    case "running":
      return <span className="animate-pulse text-amber-400">&#9673;</span>;
    case "waiting":
      return <span className="text-blue-400">&#9671;</span>;
    case "failed":
      return <span className="text-red-400">&#10007;</span>;
    default:
      return <span className="text-zinc-500">&#9675;</span>;
  }
}

function SceneCard({
  scene,
  highlight,
  imageReady,
  imageProgress,
}: {
  scene: MockScene;
  highlight?: boolean;
  imageReady?: boolean;
  imageProgress?: number;
}) {
  return (
    <div
      className={`rounded-xl border p-3 transition-all duration-300 ${
        highlight ? "border-amber-500/60 bg-amber-500/5" : "border-zinc-700 bg-zinc-800/60"
      }`}
    >
      <div className="mb-1 flex items-center gap-2">
        <span className="rounded bg-zinc-700 px-1.5 py-0.5 text-[11px] font-bold text-zinc-300">
          S{scene.scene_number}
        </span>
        {imageReady && (
          <span className="rounded bg-emerald-900/40 px-1.5 py-0.5 text-[11px] text-emerald-400">
            Image Ready
          </span>
        )}
      </div>
      <p className="mb-1 text-sm text-zinc-200">{scene.script}</p>
      <p className="text-[11px] text-zinc-500">{scene.image_prompt}</p>
      {imageProgress !== undefined && imageProgress < 100 && (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-zinc-700">
          <div
            className="h-full rounded-full bg-blue-500 transition-all duration-500"
            style={{ width: `${imageProgress}%` }}
          />
        </div>
      )}
    </div>
  );
}

// ── Main Page Component ─────────────────────────────────────
export default function PipelineDemoPage() {
  // Pipeline config
  const [config, setConfig] = useState<PipelineConfig>({
    concept: "delegated",
    script: "assisted",
    prompts: "delegated",
    images: "delegated",
    render: "delegated",
  });
  const [autoReviewThreshold, setAutoReviewThreshold] = useState(0.7);
  const [maxRevisions, setMaxRevisions] = useState(2);

  // Pipeline state
  const [stage, setStage] = useState<PipelineStage>("idle");
  const [visibleScenes, setVisibleScenes] = useState<MockScene[]>([]);
  const [qualityScore, setQualityScore] = useState<number | null>(null);
  const [revisionCount, setRevisionCount] = useState(0);
  const [imageProgress, setImageProgress] = useState<Record<number, number>>({});
  const [feedback, setFeedback] = useState("");
  const [highlightScene, setHighlightScene] = useState<number | null>(null);

  // Timer
  const [startTime, setStartTime] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [geminiCalls, setGeminiCalls] = useState(0);
  const [stageTimings, setStageTimings] = useState<Record<string, number>>({});
  const stageStartRef = useRef<number>(0);

  // Idle form
  const [topic, setTopic] = useState("검객의 성장 이야기");
  const [structure, setStructure] = useState("narrated");
  const [language, setLanguage] = useState("ko");
  const [duration, setDuration] = useState("30s");

  const running = stage !== "idle" && stage !== "completed";

  // Elapsed timer
  useEffect(() => {
    if (!startTime) return;
    if (stage === "completed") return;
    const interval = setInterval(() => {
      setElapsed(Date.now() - startTime);
    }, 100);
    return () => clearInterval(interval);
  }, [startTime, stage]);

  const markStageTime = useCallback((stageId: string) => {
    if (stageStartRef.current > 0) {
      const dur = Date.now() - stageStartRef.current;
      setStageTimings((prev) => ({ ...prev, [stageId]: dur }));
    }
    stageStartRef.current = Date.now();
  }, []);

  // Stage nodes for the status panel
  const nodes: StageNode[] = STAGE_STEPS.map((step) => {
    const configKey = step.configKey;
    const automationLabel = configKey
      ? `(${AUTOMATION_LABELS[config[configKey]].toLowerCase()})`
      : "";

    let status: NodeStatus = "pending";
    const timing = stageTimings[step.id];

    // Determine status based on current pipeline stage
    const stageOrder: PipelineStage[] = [
      "researching",
      "drafting",
      "reviewing",
      "waiting_approval",
      "revising",
      "generating_images",
      "completed",
    ];
    const stageToNodeMap: Record<string, PipelineStage[]> = {
      research: ["researching"],
      concept: ["researching"],
      script: ["drafting", "reviewing", "waiting_approval", "revising"],
      prompts: ["generating_images"],
      images: ["generating_images"],
      finalize: ["completed"],
    };

    const relevantStages = stageToNodeMap[step.id] || [];
    const currentIdx = stageOrder.indexOf(stage);

    if (stage === "completed") {
      status = "done";
    } else if (relevantStages.includes(stage)) {
      status = "running";
    } else {
      const firstRelevantIdx = Math.min(
        ...relevantStages.map((s) => stageOrder.indexOf(s)).filter((i) => i >= 0)
      );
      if (!isFinite(firstRelevantIdx)) {
        status = currentIdx >= stageOrder.length - 1 ? "done" : "pending";
      } else if (currentIdx > firstRelevantIdx) {
        status = "done";
      }
    }

    // Special: waiting_approval -> script node is "waiting"
    if (step.id === "script" && stage === "waiting_approval") {
      status = "waiting";
    }

    const children: StageNode["children"] = [];
    if (step.id === "script") {
      const scriptDone = [
        "waiting_approval",
        "revising",
        "generating_images",
        "completed",
      ].includes(stage);
      const scriptRunning = ["drafting", "reviewing"].includes(stage);

      children.push({
        label: "Draft",
        status:
          scriptDone ||
          stage === "reviewing" ||
          stage === "waiting_approval" ||
          stage === "revising"
            ? "done"
            : scriptRunning && stage === "drafting"
              ? "running"
              : "pending",
      });

      if (stage !== "idle" && stage !== "researching" && stage !== "drafting") {
        children.push({
          label: "Review",
          status: stage === "reviewing" ? "running" : qualityScore !== null ? "done" : "pending",
          detail: qualityScore !== null ? `score: ${qualityScore.toFixed(2)}` : undefined,
        });
      }

      if (stage === "waiting_approval") {
        children.push({ label: "Your Review", status: "waiting" });
      }
      if (
        stage === "revising" ||
        (revisionCount > 0 && ["generating_images", "completed"].includes(stage))
      ) {
        children.push({
          label: `Revision ${revisionCount}/${maxRevisions}`,
          status: stage === "revising" ? "running" : "done",
        });
      }
    }

    return {
      id: step.id,
      label: step.label,
      status,
      detail: automationLabel,
      elapsed: timing,
      children: children.length > 0 ? children : undefined,
    };
  });

  // ── Pipeline Simulation ─────────────────────────────────
  const startPipeline = useCallback(() => {
    setStage("researching");
    setStartTime(Date.now());
    setElapsed(0);
    setGeminiCalls(0);
    setVisibleScenes([]);
    setQualityScore(null);
    setRevisionCount(0);
    setImageProgress({});
    setStageTimings({});
    setHighlightScene(null);
    stageStartRef.current = Date.now();
  }, []);

  // Researching -> Drafting
  useEffect(() => {
    if (stage !== "researching") return;
    const timer = setTimeout(() => {
      markStageTime("research");
      setGeminiCalls((c) => c + 1);
      setStage("drafting");
    }, 1500);
    return () => clearTimeout(timer);
  }, [stage, markStageTime]);

  // Drafting: add scenes one by one
  useEffect(() => {
    if (stage !== "drafting") return;
    const idx = visibleScenes.length;
    if (idx >= MOCK_SCENES.length) {
      markStageTime("script");
      setGeminiCalls((c) => c + 1);
      setStage("reviewing");
      return;
    }
    const timer = setTimeout(() => {
      setVisibleScenes((prev) => [...prev, MOCK_SCENES[idx]]);
    }, 800);
    return () => clearTimeout(timer);
  }, [stage, visibleScenes.length, markStageTime]);

  // Reviewing -> next
  useEffect(() => {
    if (stage !== "reviewing") return;
    const timer = setTimeout(() => {
      const score = 0.82;
      setQualityScore(score);
      markStageTime("concept");

      if (config.script === "assisted") {
        setStage("waiting_approval");
      } else if (score < autoReviewThreshold && revisionCount < maxRevisions) {
        setStage("revising");
      } else {
        proceedToImages();
      }
    }, 1000);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);

  // Revising
  useEffect(() => {
    if (stage !== "revising") return;
    setRevisionCount((c) => c + 1);
    setHighlightScene(2);
    const timer = setTimeout(() => {
      setHighlightScene(null);
      setQualityScore(0.88);
      proceedToImages();
    }, 2000);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);

  // Generating images
  useEffect(() => {
    if (stage !== "generating_images") return;
    let current = 0;
    const interval = setInterval(() => {
      current++;
      if (current > MOCK_SCENES.length) {
        clearInterval(interval);
        markStageTime("images");
        setStage("completed");
        return;
      }
      // Complete previous scene
      if (current > 1) {
        setImageProgress((prev) => ({ ...prev, [current - 1]: 100 }));
      }
      // Start new scene progress
      if (current <= MOCK_SCENES.length) {
        setImageProgress((prev) => ({ ...prev, [current]: 50 }));
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [stage, markStageTime]);

  function proceedToImages() {
    if (config.images === "delegated" || config.images === "assisted") {
      markStageTime("prompts");
      setGeminiCalls((c) => c + 1);
      setStage("generating_images");
    } else {
      markStageTime("prompts");
      setStage("completed");
    }
  }

  function handleApprove() {
    proceedToImages();
  }

  function handleRequestEdit() {
    if (feedback.trim()) {
      setStage("revising");
      setFeedback("");
    }
  }

  function handleReset() {
    setStage("idle");
    setStartTime(null);
    setElapsed(0);
    setGeminiCalls(0);
    setVisibleScenes([]);
    setQualityScore(null);
    setRevisionCount(0);
    setImageProgress({});
    setStageTimings({});
    setHighlightScene(null);
  }

  function applyPreset(preset: PipelineConfig) {
    setConfig(preset);
  }

  // ── Render ────────────────────────────────────────────────
  return (
    <div className="flex h-[calc(100vh-var(--nav-height))] flex-col overflow-hidden bg-zinc-900">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-700/60 px-6 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-bold text-zinc-100">Pipeline Demo</h1>
          <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[11px] font-medium text-zinc-400">
            Mock Simulation
          </span>
        </div>
        {stage !== "idle" && (
          <button
            onClick={handleReset}
            className="rounded-lg bg-zinc-800 px-3 py-1 text-xs font-medium text-zinc-300 hover:bg-zinc-700"
          >
            Reset
          </button>
        )}
      </div>

      {/* 3-Column Layout */}
      <div className="grid flex-1 grid-cols-[280px_1fr_280px] overflow-hidden">
        {/* Left: Pipeline Control */}
        <LeftPanel
          config={config}
          setConfig={setConfig}
          autoReviewThreshold={autoReviewThreshold}
          setAutoReviewThreshold={setAutoReviewThreshold}
          maxRevisions={maxRevisions}
          setMaxRevisions={setMaxRevisions}
          running={running}
          stage={stage}
          onStart={startPipeline}
          onApplyPreset={applyPreset}
        />

        {/* Center: Main Content */}
        <CenterPanel
          stage={stage}
          config={config}
          visibleScenes={visibleScenes}
          qualityScore={qualityScore}
          revisionCount={revisionCount}
          maxRevisions={maxRevisions}
          imageProgress={imageProgress}
          highlightScene={highlightScene}
          feedback={feedback}
          setFeedback={setFeedback}
          elapsed={elapsed}
          geminiCalls={geminiCalls}
          topic={topic}
          setTopic={setTopic}
          structure={structure}
          setStructure={setStructure}
          language={language}
          setLanguage={setLanguage}
          duration={duration}
          setDuration={setDuration}
          onStart={startPipeline}
          onApprove={handleApprove}
          onRequestEdit={handleRequestEdit}
        />

        {/* Right: Status Panel */}
        <RightPanel
          nodes={nodes}
          elapsed={elapsed}
          geminiCalls={geminiCalls}
          revisionCount={revisionCount}
          maxRevisions={maxRevisions}
          stage={stage}
        />
      </div>
    </div>
  );
}

// ── Left Panel ──────────────────────────────────────────────
function LeftPanel({
  config,
  setConfig,
  autoReviewThreshold,
  setAutoReviewThreshold,
  maxRevisions,
  setMaxRevisions,
  running,
  stage,
  onStart,
  onApplyPreset,
}: {
  config: PipelineConfig;
  setConfig: (c: PipelineConfig) => void;
  autoReviewThreshold: number;
  setAutoReviewThreshold: (v: number) => void;
  maxRevisions: number;
  setMaxRevisions: (v: number) => void;
  running: boolean;
  stage: PipelineStage;
  onStart: () => void;
  onApplyPreset: (c: PipelineConfig) => void;
}) {
  const updateConfig = (key: keyof PipelineConfig, value: AutomationLevel) => {
    setConfig({ ...config, [key]: value });
  };

  const disabled = running;

  return (
    <div className="bg-zinc-850 flex flex-col gap-4 overflow-y-auto border-r border-zinc-700/60 p-4">
      {/* Section: Automation Levels */}
      <div>
        <h2 className="mb-3 text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
          Pipeline Control
        </h2>
        <div className="space-y-2">
          {(["concept", "script", "prompts", "images", "render"] as const).map((key) => (
            <LevelSelect
              key={key}
              label={key.charAt(0).toUpperCase() + key.slice(1)}
              value={config[key]}
              onChange={(v) => updateConfig(key, v)}
              disabled={disabled}
            />
          ))}
        </div>
      </div>

      {/* Section: Presets */}
      <div>
        <h2 className="mb-2 text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
          Presets
        </h2>
        <div className="space-y-1.5">
          {PRESETS.map((preset) => {
            const isActive = Object.entries(preset.config).every(
              ([k, v]) => config[k as keyof PipelineConfig] === v
            );
            return (
              <button
                key={preset.label}
                onClick={() => onApplyPreset(preset.config)}
                disabled={disabled}
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition ${
                  isActive
                    ? "bg-zinc-700 text-zinc-100"
                    : "bg-zinc-800/60 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-300"
                } disabled:opacity-40`}
              >
                <span className="text-sm">
                  {preset.icon === "direct_hit"
                    ? "\uD83C\uDFAF"
                    : preset.icon === "robot"
                      ? "\uD83E\uDD16"
                      : "\u270D\uFE0F"}
                </span>
                {preset.label}
                {isActive && <span className="ml-auto text-[11px] text-emerald-400">Active</span>}
              </button>
            );
          })}
        </div>
      </div>

      {/* Section: Settings */}
      <div>
        <h2 className="mb-2 text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
          Settings
        </h2>
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-zinc-400">Auto-review</span>
            <input
              type="number"
              step={0.1}
              min={0}
              max={1}
              value={autoReviewThreshold}
              onChange={(e) => setAutoReviewThreshold(parseFloat(e.target.value) || 0)}
              disabled={disabled}
              className="w-16 rounded-lg border border-zinc-600 bg-zinc-700 px-2 py-1 text-center text-xs text-zinc-200 outline-none disabled:opacity-40"
            />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-zinc-400">Max revisions</span>
            <input
              type="number"
              min={0}
              max={5}
              value={maxRevisions}
              onChange={(e) => setMaxRevisions(parseInt(e.target.value) || 0)}
              disabled={disabled}
              className="w-16 rounded-lg border border-zinc-600 bg-zinc-700 px-2 py-1 text-center text-xs text-zinc-200 outline-none disabled:opacity-40"
            />
          </div>
        </div>
      </div>

      {/* Start Button */}
      <button
        onClick={onStart}
        disabled={running || stage === "completed"}
        className="mt-auto flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-emerald-500 disabled:opacity-40"
      >
        <span>{"\u25B6"}</span>
        Start Pipeline
      </button>
    </div>
  );
}

// ── Center Panel ────────────────────────────────────────────
function CenterPanel({
  stage,
  config,
  visibleScenes,
  qualityScore,
  revisionCount,
  maxRevisions,
  imageProgress,
  highlightScene,
  feedback,
  setFeedback,
  elapsed,
  geminiCalls,
  topic,
  setTopic,
  structure,
  setStructure,
  language,
  setLanguage,
  duration,
  setDuration,
  onStart,
  onApprove,
  onRequestEdit,
}: {
  stage: PipelineStage;
  config: PipelineConfig;
  visibleScenes: MockScene[];
  qualityScore: number | null;
  revisionCount: number;
  maxRevisions: number;
  imageProgress: Record<number, number>;
  highlightScene: number | null;
  feedback: string;
  setFeedback: (v: string) => void;
  elapsed: number;
  geminiCalls: number;
  topic: string;
  setTopic: (v: string) => void;
  structure: string;
  setStructure: (v: string) => void;
  language: string;
  setLanguage: (v: string) => void;
  duration: string;
  setDuration: (v: string) => void;
  onStart: () => void;
  onApprove: () => void;
  onRequestEdit: () => void;
}) {
  return (
    <div className="flex flex-col overflow-y-auto bg-zinc-900 p-6">
      {stage === "idle" && (
        <IdleView
          topic={topic}
          setTopic={setTopic}
          structure={structure}
          setStructure={setStructure}
          language={language}
          setLanguage={setLanguage}
          duration={duration}
          setDuration={setDuration}
          onStart={onStart}
        />
      )}

      {stage === "researching" && <ResearchingView />}

      {stage === "drafting" && <DraftingView scenes={visibleScenes} />}

      {stage === "reviewing" && <ReviewingView qualityScore={qualityScore} />}

      {stage === "waiting_approval" && (
        <WaitingApprovalView
          scenes={visibleScenes}
          qualityScore={qualityScore}
          feedback={feedback}
          setFeedback={setFeedback}
          onApprove={onApprove}
          onRequestEdit={onRequestEdit}
        />
      )}

      {stage === "revising" && (
        <RevisingView
          scenes={visibleScenes}
          highlightScene={highlightScene}
          revisionCount={revisionCount}
          maxRevisions={maxRevisions}
        />
      )}

      {stage === "generating_images" && (
        <GeneratingImagesView scenes={visibleScenes} imageProgress={imageProgress} />
      )}

      {stage === "completed" && (
        <CompletedView
          elapsed={elapsed}
          geminiCalls={geminiCalls}
          scenesCount={MOCK_SCENES.length}
        />
      )}
    </div>
  );
}

// ── Center: Stage Views ─────────────────────────────────────

function IdleView({
  topic,
  setTopic,
  structure,
  setStructure,
  language,
  setLanguage,
  duration,
  setDuration,
  onStart,
}: {
  topic: string;
  setTopic: (v: string) => void;
  structure: string;
  setStructure: (v: string) => void;
  language: string;
  setLanguage: (v: string) => void;
  duration: string;
  setDuration: (v: string) => void;
  onStart: () => void;
}) {
  return (
    <div className="mx-auto flex w-full max-w-lg flex-col gap-6 pt-12">
      <div className="text-center">
        <h2 className="mb-1 text-lg font-bold text-zinc-100">Agentic Pipeline</h2>
        <p className="text-sm text-zinc-400">Topic과 설정을 입력하고 파이프라인을 시작하세요.</p>
      </div>

      <div className="space-y-4 rounded-2xl border border-zinc-700 bg-zinc-800/60 p-5">
        <div>
          <label className="mb-1 block text-xs font-semibold text-zinc-400">Topic</label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="w-full rounded-lg border border-zinc-600 bg-zinc-700 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-zinc-400"
            placeholder="예: 검객의 성장 이야기"
          />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="mb-1 block text-xs font-semibold text-zinc-400">Structure</label>
            <select
              value={structure}
              onChange={(e) => setStructure(e.target.value)}
              className="w-full rounded-lg border border-zinc-600 bg-zinc-700 px-2 py-2 text-xs text-zinc-200 outline-none"
            >
              <option value="narrated">Narrated</option>
              <option value="dialogue">Dialogue</option>
              <option value="montage">Montage</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-zinc-400">Language</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full rounded-lg border border-zinc-600 bg-zinc-700 px-2 py-2 text-xs text-zinc-200 outline-none"
            >
              <option value="ko">Korean</option>
              <option value="en">English</option>
              <option value="ja">Japanese</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-zinc-400">Duration</label>
            <select
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              className="w-full rounded-lg border border-zinc-600 bg-zinc-700 px-2 py-2 text-xs text-zinc-200 outline-none"
            >
              <option value="30s">30s</option>
              <option value="60s">60s</option>
              <option value="90s">90s</option>
            </select>
          </div>
        </div>
      </div>

      <button
        onClick={onStart}
        className="flex items-center justify-center gap-2 rounded-xl bg-emerald-600 py-3 text-sm font-bold text-white hover:bg-emerald-500"
      >
        <span>{"\u25B6"}</span> Start Pipeline
      </button>
    </div>
  );
}

function ResearchingView() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-zinc-600 border-t-amber-400" />
      <div className="text-center">
        <p className="text-sm font-semibold text-zinc-200">Researching...</p>
        <p className="mt-1 text-xs text-zinc-500">
          캐릭터 컨텍스트와 그룹 설정을 로드하고 있습니다
        </p>
      </div>
    </div>
  );
}

function DraftingView({ scenes }: { scenes: MockScene[] }) {
  return (
    <div className="space-y-3">
      <div className="mb-4 flex items-center gap-2">
        <div className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
        <h2 className="text-sm font-bold text-zinc-200">
          Drafting Script ({scenes.length}/{MOCK_SCENES.length})
        </h2>
      </div>
      <div className="space-y-2">
        {scenes.map((scene) => (
          <div
            key={scene.scene_number}
            className="animate-fadeIn rounded-xl border border-zinc-700 bg-zinc-800/60 p-3"
            style={{
              animation: "fadeSlideIn 0.4s ease-out forwards",
            }}
          >
            <div className="mb-1 flex items-center gap-2">
              <span className="rounded bg-zinc-700 px-1.5 py-0.5 text-[11px] font-bold text-zinc-300">
                S{scene.scene_number}
              </span>
            </div>
            <p className="text-sm text-zinc-200">{scene.script}</p>
            <p className="mt-1 text-[11px] text-zinc-500">{scene.image_prompt}</p>
          </div>
        ))}
      </div>
      {/* CSS for fade-in animation */}
      <style jsx>{`
        @keyframes fadeSlideIn {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}

function ReviewingView({ qualityScore }: { qualityScore: number | null }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4">
      {qualityScore === null ? (
        <>
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-zinc-600 border-t-blue-400" />
          <p className="text-sm font-semibold text-zinc-200">Checking quality...</p>
        </>
      ) : (
        <div className="text-center">
          <div className="mb-2 text-4xl font-bold text-emerald-400">{qualityScore.toFixed(2)}</div>
          <p className="text-sm text-zinc-400">Quality Score</p>
        </div>
      )}
    </div>
  );
}

function WaitingApprovalView({
  scenes,
  qualityScore,
  feedback,
  setFeedback,
  onApprove,
  onRequestEdit,
}: {
  scenes: MockScene[];
  qualityScore: number | null;
  feedback: string;
  setFeedback: (v: string) => void;
  onApprove: () => void;
  onRequestEdit: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-blue-400">{"\u2B50"}</span>
          <h2 className="text-sm font-bold text-zinc-200">Waiting for Your Approval</h2>
        </div>
        {qualityScore !== null && (
          <span className="rounded-full bg-emerald-900/40 px-2 py-0.5 text-xs text-emerald-400">
            Score: {qualityScore.toFixed(2)}
          </span>
        )}
      </div>

      <div className="space-y-2">
        {scenes.map((scene) => (
          <div
            key={scene.scene_number}
            className="rounded-xl border border-zinc-700 bg-zinc-800/40 p-3"
          >
            <div className="mb-1 flex items-center gap-2">
              <span className="rounded bg-zinc-700 px-1.5 py-0.5 text-[11px] font-bold text-zinc-300">
                S{scene.scene_number}
              </span>
            </div>
            <p className="text-sm text-zinc-300">{scene.script}</p>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-zinc-600 bg-zinc-800/60 p-4">
        <label className="mb-1 block text-xs font-semibold text-zinc-400">
          Feedback (optional)
        </label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          rows={2}
          placeholder="수정이 필요한 부분을 설명해주세요..."
          className="w-full rounded-lg border border-zinc-600 bg-zinc-700 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-zinc-400"
        />
        <div className="mt-3 flex gap-2">
          <button
            onClick={onApprove}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-500"
          >
            Approve All
          </button>
          <button
            onClick={onRequestEdit}
            disabled={!feedback.trim()}
            className="rounded-lg bg-zinc-700 px-4 py-2 text-xs font-bold text-zinc-300 hover:bg-zinc-600 disabled:opacity-40"
          >
            Request Edit
          </button>
        </div>
      </div>
    </div>
  );
}

function RevisingView({
  scenes,
  highlightScene,
  revisionCount,
  maxRevisions,
}: {
  scenes: MockScene[];
  highlightScene: number | null;
  revisionCount: number;
  maxRevisions: number;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
        <h2 className="text-sm font-bold text-zinc-200">
          Auto-revising ({revisionCount}/{maxRevisions})...
        </h2>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-zinc-700">
        <div className="h-full w-1/2 animate-pulse rounded-full bg-amber-500" />
      </div>

      <div className="space-y-2">
        {scenes.map((scene) => (
          <SceneCard
            key={scene.scene_number}
            scene={scene}
            highlight={scene.scene_number === highlightScene}
          />
        ))}
      </div>
    </div>
  );
}

function GeneratingImagesView({
  scenes,
  imageProgress,
}: {
  scenes: MockScene[];
  imageProgress: Record<number, number>;
}) {
  const completedCount = Object.values(imageProgress).filter((p) => p >= 100).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="h-2 w-2 animate-pulse rounded-full bg-blue-400" />
        <h2 className="text-sm font-bold text-zinc-200">
          Generating Images ({completedCount}/{scenes.length})
        </h2>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {scenes.map((scene) => {
          const progress = imageProgress[scene.scene_number] ?? 0;
          const ready = progress >= 100;
          return (
            <div
              key={scene.scene_number}
              className="overflow-hidden rounded-xl border border-zinc-700 bg-zinc-800/60"
            >
              {/* Image placeholder */}
              <div className="flex aspect-[9/16] max-h-48 items-center justify-center bg-zinc-800">
                {ready ? (
                  <div className="flex flex-col items-center gap-1 text-emerald-400">
                    <span className="text-2xl">{"\u2713"}</span>
                    <span className="text-[11px]">Done</span>
                  </div>
                ) : progress > 0 ? (
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-blue-400" />
                ) : (
                  <span className="text-xs text-zinc-600">Pending</span>
                )}
              </div>
              <div className="p-2">
                <span className="text-[11px] font-bold text-zinc-400">S{scene.scene_number}</span>
                <p className="truncate text-[11px] text-zinc-500">{scene.script}</p>
                {progress > 0 && progress < 100 && (
                  <div className="mt-1 h-1 overflow-hidden rounded-full bg-zinc-700">
                    <div
                      className="h-full rounded-full bg-blue-500 transition-all duration-500"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CompletedView({
  elapsed,
  geminiCalls,
  scenesCount,
}: {
  elapsed: number;
  geminiCalls: number;
  scenesCount: number;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-900/40">
        <span className="text-3xl text-emerald-400">{"\u2713"}</span>
      </div>
      <div className="text-center">
        <h2 className="text-lg font-bold text-zinc-100">Pipeline Complete!</h2>
        <p className="mt-1 text-sm text-zinc-400">{scenesCount} scenes generated successfully.</p>
      </div>

      <div className="grid grid-cols-3 gap-6 text-center">
        <div>
          <div className="text-xl font-bold text-zinc-200">{formatElapsed(elapsed)}</div>
          <div className="text-xs text-zinc-500">Total Time</div>
        </div>
        <div>
          <div className="text-xl font-bold text-zinc-200">{geminiCalls}</div>
          <div className="text-xs text-zinc-500">Gemini Calls</div>
        </div>
        <div>
          <div className="text-xl font-bold text-zinc-200">{scenesCount}</div>
          <div className="text-xs text-zinc-500">Scenes</div>
        </div>
      </div>

      <button
        onClick={() => {}}
        className="rounded-xl bg-zinc-800 px-6 py-2.5 text-sm font-medium text-zinc-300 hover:bg-zinc-700"
      >
        View in Edit Tab
      </button>
    </div>
  );
}

// ── Right Panel ─────────────────────────────────────────────
function RightPanel({
  nodes,
  elapsed,
  geminiCalls,
  revisionCount,
  maxRevisions,
  stage,
}: {
  nodes: StageNode[];
  elapsed: number;
  geminiCalls: number;
  revisionCount: number;
  maxRevisions: number;
  stage: PipelineStage;
}) {
  return (
    <div className="bg-zinc-850 flex flex-col gap-4 overflow-y-auto border-l border-zinc-700/60 p-4">
      {/* Pipeline Status */}
      <div>
        <h2 className="mb-3 text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
          Pipeline Status
        </h2>
        <div className="space-y-1">
          {nodes.map((node) => (
            <div key={node.id}>
              <div className="flex items-center gap-2 rounded-lg px-2 py-1">
                <NodeIcon status={node.status} />
                <span
                  className={`text-xs font-medium ${
                    node.status === "running"
                      ? "text-amber-300"
                      : node.status === "done"
                        ? "text-zinc-300"
                        : node.status === "waiting"
                          ? "text-blue-300"
                          : "text-zinc-500"
                  }`}
                >
                  {node.label}
                </span>
                {node.detail && (
                  <span
                    className={`ml-auto text-[11px] ${AUTOMATION_COLORS[node.detail.replace(/[()]/g, "") as AutomationLevel] || "text-zinc-500"}`}
                  >
                    {node.detail}
                  </span>
                )}
                {node.elapsed && (
                  <span className="ml-auto text-[11px] text-zinc-500">
                    {formatElapsed(node.elapsed)}
                  </span>
                )}
              </div>
              {/* Children */}
              {node.children && (
                <div className="ml-4 border-l border-zinc-700 pl-3">
                  {node.children.map((child, idx) => (
                    <div key={idx} className="flex items-center gap-2 py-0.5">
                      <NodeIcon status={child.status} />
                      <span className="text-[11px] text-zinc-400">{child.label}</span>
                      {child.detail && (
                        <span className="ml-auto text-[11px] text-zinc-500">{child.detail}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div>
        <h2 className="mb-2 text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
          Stats
        </h2>
        <div className="space-y-1.5 rounded-xl border border-zinc-700 bg-zinc-800/40 p-3">
          <StatRow label="Elapsed" value={stage === "idle" ? "--" : formatElapsed(elapsed)} />
          <StatRow label="Gemini calls" value={`${geminiCalls}`} />
          <StatRow label="Revisions" value={`${revisionCount}/${maxRevisions}`} />
        </div>
      </div>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-xs font-medium text-zinc-300">{value}</span>
    </div>
  );
}
