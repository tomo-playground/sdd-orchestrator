"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import axios from "axios";
import { useStudioStore, resetStudioStore } from "../store/useStudioStore";
import type { StudioTab } from "../store/slices/metaSlice";
import type { Scene, AutoRunStepId } from "../types";
import { API_BASE, PROMPT_APPLY_KEY } from "../constants";
import TabBar from "../components/studio/TabBar";
import PlanTab from "../components/studio/PlanTab";
import ScenesTab from "../components/studio/ScenesTab";
import OutputTab from "../components/studio/OutputTab";
import InsightsTab from "../components/studio/InsightsTab";
import Toast from "../components/ui/Toast";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import ImagePreviewModal from "../components/ui/ImagePreviewModal";
import VideoPreviewModal from "../components/ui/VideoPreviewModal";
import AutoRunStatus from "../components/storyboard/AutoRunStatus";
import ChannelProfileModal from "../components/setup/ChannelProfileModal";
import StyleProfileModal from "../components/setup/StyleProfileModal";
import { useAutopilot } from "../hooks/useAutopilot";
import { runAutoRunFromStep } from "../store/actions/autopilotActions";
import PromptHelperSidebar from "../components/prompt/PromptHelperSidebar";
import { suggestPromptSplit, copyPromptHelperText } from "../store/actions/promptHelperActions";
import { autoSaveStoryboard } from "../store/actions/storyboardActions";

function StudioContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const storyboardId = searchParams.get("id");
  const [isLoadingDb, setIsLoadingDb] = useState(false);
  const [showChannelProfileModal, setShowChannelProfileModal] = useState(false);
  const [showStyleProfileModal, setShowStyleProfileModal] = useState(false);
  const [loadedProfileId, setLoadedProfileId] = useState<number | null>(null);

  const activeTab = useStudioStore((s) => s.activeTab);
  const setActiveTab = useStudioStore((s) => s.setActiveTab);
  const toast = useStudioStore((s) => s.toast);
  const setMeta = useStudioStore((s) => s.setMeta);
  const setScenes = useStudioStore((s) => s.setScenes);
  const setPlan = useStudioStore((s) => s.setPlan);
  const scenes = useStudioStore((s) => s.scenes);
  const storyboardTitle = useStudioStore((s) => s.storyboardTitle);
  const imagePreviewSrc = useStudioStore((s) => s.imagePreviewSrc);
  const imagePreviewCandidates = useStudioStore((s) => s.imagePreviewCandidates);
  const videoPreviewSrc = useStudioStore((s) => s.videoPreviewSrc);
  const channelProfile = useStudioStore((s) => s.channelProfile);
  const hasValidProfile = useStudioStore((s) => s.hasValidProfile);
  const setChannelProfile = useStudioStore((s) => s.setChannelProfile);
  const setChannelAvatarUrl = useStudioStore((s) => s.setChannelAvatarUrl);
  const currentStyleProfile = useStudioStore((s) => s.currentStyleProfile);
  const setOutput = useStudioStore((s) => s.setOutput);
  const showToast = useStudioStore((s) => s.showToast);

  // Meta for Prompt Helper
  const isHelperOpen = useStudioStore((s) => s.isHelperOpen);
  const examplePrompt = useStudioStore((s) => s.examplePrompt);
  const suggestedBase = useStudioStore((s) => s.suggestedBase);
  const suggestedScene = useStudioStore((s) => s.suggestedScene);
  const isSuggesting = useStudioStore((s) => s.isSuggesting);
  const copyStatus = useStudioStore((s) => s.copyStatus);

  // Autopilot state (shared across all tabs)
  const autopilot = useAutopilot();

  // Load Style Profile function
  const loadStyleProfile = useCallback(async (profileId: number) => {
    try {
      // 1. 프로필 상세 정보 조회
      const res = await axios.get(`${API_BASE}/style-profiles/${profileId}`);
      const profile = res.data;

      // 2. Store에 프로필 정보 저장
      setOutput({
        currentStyleProfile: {
          id: profile.id,
          name: profile.name,
          display_name: profile.display_name,
          sd_model_name: profile.sd_model?.name || profile.sd_model?.display_name || null,
          loras: profile.loras || [],
          negative_embeddings: profile.negative_embeddings || [],
          positive_embeddings: profile.positive_embeddings || [],
          default_positive: profile.default_positive,
          default_negative: profile.default_negative,
        },
      });

      // 3. SD Model 변경 (백그라운드)
      if (profile.sd_model?.name) {
        axios
          .post(`${API_BASE}/sd/options`, {
            sd_model_checkpoint: profile.sd_model.name,
          })
          .then(() => {
            showToast(
              `스타일 프로필 "${profile.display_name || profile.name}" 로드 완료\n` +
              `Model: ${profile.sd_model.name}\n` +
              `LoRAs: ${profile.loras?.length || 0}개\n` +
              `Embeddings: ${(profile.negative_embeddings?.length || 0) + (profile.positive_embeddings?.length || 0)}개`,
              "success"
            );
          })
          .catch((err) => {
            console.error("Failed to change SD model:", err);
            showToast(
              `프로필은 로드되었으나 Model 변경 실패: ${profile.sd_model.name}`,
              "error"
            );
          });
      } else {
        showToast(`스타일 프로필 "${profile.display_name || profile.name}"이(가) 로드되었습니다.`, "success");
      }
    } catch (error) {
      console.error("Failed to load style profile:", error);
      showToast("스타일 프로필 로드 실패", "error");
    }
  }, [setOutput, showToast]);

  // Channel Profile Onboarding (첫 진입 시 자동 표시)
  useEffect(() => {
    const hasProfile = hasValidProfile();
    const hasSeenOnboarding = localStorage.getItem("channel_onboarding_done");

    if (!hasProfile && !hasSeenOnboarding) {
      setShowChannelProfileModal(true);
      localStorage.setItem("channel_onboarding_done", "true");
    }
  }, [hasValidProfile]);

  // Style Profile Selection (새 스토리보드만)
  useEffect(() => {
    const hasProfile = hasValidProfile();

    // 기존 스토리보드 로드 중이거나 채널 프로필 모달 표시 중이면 스킵
    if (isLoadingDb || storyboardId || showChannelProfileModal) {
      return;
    }

    // 프로필이 없고 현재 스타일 프로필도 없으면 모달 표시 (새 스토리보드)
    if (hasProfile && !currentStyleProfile) {
      const styleOnboardingDone = sessionStorage.getItem("style_onboarding_done");
      if (!styleOnboardingDone) {
        setShowStyleProfileModal(true);
        sessionStorage.setItem("style_onboarding_done", "true");
      }
    }
  }, [hasValidProfile, currentStyleProfile, showChannelProfileModal, isLoadingDb, storyboardId]);

  // Load channel avatar URL when profile changes
  useEffect(() => {
    if (!channelProfile?.avatar_key) {
      setChannelAvatarUrl(null);
      return;
    }

    // Use the same URL pattern as ChannelProfileModal
    const url = `${API_BASE}/controlnet/ip-adapter/reference/${channelProfile.avatar_key}/image?t=${Date.now()}`;
    setChannelAvatarUrl(url);
  }, [channelProfile?.avatar_key, setChannelAvatarUrl]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) return;

      const { scenes: sc, currentSceneIndex: idx } = useStudioStore.getState();
      if (e.key === "ArrowLeft" && sc.length > 0) {
        e.preventDefault();
        useStudioStore.getState().setCurrentSceneIndex(Math.max(0, idx - 1));
      }
      if (e.key === "ArrowRight" && sc.length > 0) {
        e.preventDefault();
        useStudioStore.getState().setCurrentSceneIndex(Math.min(sc.length - 1, idx + 1));
      }
      if (e.key === "Escape") {
        useStudioStore.getState().setMeta({ imagePreviewSrc: null, videoPreviewSrc: null });
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Reset store only when explicitly creating a new storyboard or switching IDs
  useEffect(() => {
    const isNewStoryboard = searchParams.get("new") === "true";
    if (isNewStoryboard) {
      resetStudioStore();
      // Clear the 'new' AND 'id' params to prevent loading old storyboard
      const url = new URL(window.location.href);
      url.searchParams.delete("new");
      url.searchParams.delete("id");  // CRITICAL: Remove storyboard ID
      window.history.replaceState({}, "", url.toString());
    }
  }, [searchParams]);

  // Handle case where user navigates between existing storyboards directly
  useEffect(() => {
    if (storyboardId) {
      // Clear transient session data when ID changes
      // but don't reset everything yet because we're about to load from DB
      useStudioStore.getState().setOutput({
        videoUrl: null,
        videoUrlFull: null,
        videoUrlPost: null,
        recentVideos: [],
      });
    }
  }, [storyboardId]);

  // Apply prompt from localStorage (from /manage Prompts tab)
  useEffect(() => {
    const stored = window.localStorage.getItem(PROMPT_APPLY_KEY);
    if (!stored) return;
    try {
      const data = JSON.parse(stored) as Record<string, unknown>;
      const plan: Record<string, unknown> = {};
      if (data.positive_prompt) plan.basePromptA = data.positive_prompt;
      if (data.negative_prompt) plan.baseNegativePromptA = data.negative_prompt;
      if (data.steps) plan.baseStepsA = data.steps;
      if (data.cfg_scale) plan.baseCfgScaleA = data.cfg_scale;
      if (data.sampler_name) plan.baseSamplerA = data.sampler_name;
      if (data.seed) plan.baseSeedA = data.seed;
      if (data.clip_skip) plan.baseClipSkipA = data.clip_skip;
      setPlan(plan);

      // Apply to current scene if exists
      const { scenes: sc, currentSceneIndex: idx, updateScene } = useStudioStore.getState();
      if (sc.length > 0 && sc[idx]) {
        const updates: Partial<Scene> = {};
        if (data.positive_prompt) updates.image_prompt = data.positive_prompt as string;
        if (data.negative_prompt) updates.negative_prompt = data.negative_prompt as string;
        if (data.steps) updates.steps = data.steps as number;
        if (data.cfg_scale) updates.cfg_scale = data.cfg_scale as number;
        if (data.sampler_name) updates.sampler_name = data.sampler_name as string;
        if (data.seed) updates.seed = data.seed as number;
        if (data.clip_skip) updates.clip_skip = data.clip_skip as number;
        if (data.context_tags) updates.context_tags = data.context_tags as Record<string, string[]>;
        if (data.id) updates.prompt_history_id = data.id as number;
        updateScene(sc[idx].id, updates);
      }
      window.localStorage.removeItem(PROMPT_APPLY_KEY);
      useStudioStore.getState().showToast("Prompt applied!", "success");
    } catch {
      window.localStorage.removeItem(PROMPT_APPLY_KEY);
    }
  }, [setPlan]);

  // Load storyboard from DB if ?id=X
  useEffect(() => {
    if (!storyboardId) return;
    const id = parseInt(storyboardId, 10);
    if (isNaN(id)) return;

    setIsLoadingDb(true);
    axios
      .get(`${API_BASE}/storyboards/${id}`)
      .then((res) => {
        const data = res.data;
        setMeta({
          storyboardId: data.id,
          storyboardTitle: data.title,
          activeTab: data.scenes?.length > 0 ? "scenes" : "plan",
        });
        // Load video results and caption into output slice
        useStudioStore.getState().setOutput({
          videoUrl: data.video_url || null,
          videoUrlFull: data.video_url || null, // Fallback
          recentVideos: data.recent_videos || [],
          videoCaption: data.default_caption || "",
        });
        setPlan({
          selectedCharacterId: data.default_character_id || null,
          topic: data.description || "",
        });

        // Load character LoRAs if character is selected
        if (data.default_character_id) {
          axios.get(`${API_BASE}/characters/${data.default_character_id}`)
            .then((charRes) => {
              const char = charRes.data;
              setPlan({
                characterLoras: char.loras || [],
                characterPromptMode: char.prompt_mode || "auto",
                basePromptA: char.base_prompt || "",
                baseNegativePromptA: char.base_negative || "",
              });
            })
            .catch((err) => {
              console.error("Failed to load character:", err);
            });
        }

        // Load style profile automatically if set
        if (data.default_style_profile_id) {
          loadStyleProfile(data.default_style_profile_id);
        } else {
          // No profile set - show modal for selection
          setShowStyleProfileModal(true);
        }

        // Map DB scenes → frontend Scene type
        if (data.scenes?.length > 0) {
          const mapped: Scene[] = data.scenes.map((s: Record<string, unknown>, i: number) => ({
            id: (s.id as number) || i,  // Use DB ID if available, fallback to index
            script: s.script || "",
            speaker: s.speaker || "Narrator",
            duration: s.duration || 3,
            image_prompt: s.image_prompt || "",
            image_prompt_ko: s.image_prompt_ko || "",
            image_url: s.image_url || null,
            image_asset_id: (s.image_asset_id as number) || null,
            description: s.description || "",
            width: s.width || 512,
            height: s.height || 768,
            negative_prompt: s.negative_prompt || "",
            steps: s.steps || 27,
            cfg_scale: s.cfg_scale || 7,
            sampler_name: s.sampler_name || "DPM++ 2M Karras",
            seed: s.seed || -1,
            clip_skip: s.clip_skip || 2,
            isGenerating: false,
            debug_payload: "",
            context_tags: s.context_tags || undefined,
          }));
          setScenes(mapped);
        }
      })
      .catch(() => {
        setMeta({ storyboardId: null });
      })
      .finally(() => setIsLoadingDb(false));
  }, [storyboardId, setMeta, setPlan, setScenes, loadStyleProfile]);

  if (isLoadingDb) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-50 via-white to-zinc-100 font-[family-name:var(--font-sans)]">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-zinc-100 bg-white/90 backdrop-blur-md transition-all duration-300">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <button
              data-testid="studio-home-btn"
              onClick={() => router.push("/")}
              className="text-xs text-zinc-500 hover:text-zinc-700"
            >
              Home
            </button>
            <span className="text-zinc-300">/</span>
            <h1 data-testid="storyboard-title" className="text-sm font-bold text-zinc-900 truncate max-w-[200px] md:max-w-md">
              {storyboardTitle || "New Storyboard"}
            </h1>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-zinc-400">
            {scenes.length > 0 && <span>{scenes.length} scenes</span>}
            {storyboardId && (
              <span className="rounded bg-zinc-100 px-2 py-0.5">
                ID: {storyboardId}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Tab Bar */}
      <TabBar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onOpenChannelProfile={() => setShowChannelProfileModal(true)}
      />

      {/* Tab Content */}
      <main className="mx-auto max-w-5xl px-6 py-8 pb-32">
        {/* Autopilot Status - Always visible */}
        {autopilot.autoRunState.status !== "idle" && (
          <div className="mb-4">
            <AutoRunStatus
              autoRunState={autopilot.autoRunState}
              autoRunLog={autopilot.autoRunLog}
              onResume={() => runAutoRunFromStep(autopilot.autoRunState.step as AutoRunStepId, autopilot)}
              onRestart={() => runAutoRunFromStep("storyboard", autopilot)}
            />
          </div>
        )}

        {/* Scenes tab uses display:none for state preservation */}
        <div data-testid="tab-content-scenes" style={{ display: activeTab === "scenes" ? "block" : "none" }}>
          <ScenesTab />
        </div>

        {activeTab === "plan" && <div data-testid="tab-content-plan"><PlanTab autopilot={autopilot} /></div>}
        {activeTab === "output" && <div data-testid="tab-content-output"><OutputTab /></div>}
        {activeTab === "insights" && <div data-testid="tab-content-insights"><InsightsTab /></div>}
      </main>

      <PromptHelperSidebar
        isOpen={isHelperOpen}
        onClose={() => setMeta({ isHelperOpen: false })}
        examplePrompt={examplePrompt}
        setExamplePrompt={(v) => setMeta({ examplePrompt: v })}
        onSuggestSplit={suggestPromptSplit}
        isSuggesting={isSuggesting}
        suggestedBase={suggestedBase}
        suggestedScene={suggestedScene}
        copyStatus={copyStatus}
        onCopyText={copyPromptHelperText}
      />

      {toast && <Toast message={toast.message} type={toast.type} />}

      <ImagePreviewModal
        src={imagePreviewSrc}
        candidates={imagePreviewCandidates || undefined}
        onClose={() => setMeta({ imagePreviewSrc: null, imagePreviewCandidates: null })}
      />

      <VideoPreviewModal
        src={videoPreviewSrc}
        onClose={() => setMeta({ videoPreviewSrc: null })}
      />

      {/* Channel Profile Modal */}
      {showChannelProfileModal && (
        <ChannelProfileModal
          initialProfile={channelProfile}
          onComplete={(profile) => {
            setChannelProfile(profile);
            setShowChannelProfileModal(false);
            showToast("채널 프로필이 저장되었습니다", "success");
            // Channel Profile 설정 후 Style Profile 선택 모달 표시 (아직 선택 안했을 때만)
            if (!currentStyleProfile) {
              setShowStyleProfileModal(true);
            }
          }}
          onCancel={() => setShowChannelProfileModal(false)}
        />
      )}

      {/* Style Profile Modal */}
      {showStyleProfileModal && (
        <StyleProfileModal
          defaultProfileId={loadedProfileId}
          onComplete={async (profile) => {
            // Store에 프로필 저장
            console.log("[StyleProfileModal] Selected profile:", profile);
            setOutput({ currentStyleProfile: profile });
            console.log("[StyleProfileModal] Store updated");
            setShowStyleProfileModal(false);

            // 스토리보드에 프로필 ID 즉시 저장
            const { storyboardId: currentId, scenes, topic, selectedCharacterId } = useStudioStore.getState();
            console.log("[StyleProfileModal] Current state:", { currentId, scenesCount: scenes.length, topic, selectedCharacterId });

            // Validate currentId is a valid number
            const validId = currentId && typeof currentId === 'number' && !isNaN(currentId) && currentId > 0;

            if (validId) {
              // 기존 스토리보드가 있으면 업데이트
              try {
                await axios.put(`${API_BASE}/storyboards/${currentId}`, {
                  title: topic || "Untitled",
                  description: topic,
                  default_character_id: selectedCharacterId,
                  default_style_profile_id: profile.id,
                  scenes: scenes.map((s, i) => ({
                    scene_id: i,
                    script: s.script,
                    speaker: s.speaker,
                    duration: s.duration,
                    image_prompt: s.image_prompt,
                    image_prompt_ko: s.image_prompt_ko,
                    image_url: s.image_url,
                    description: s.description,
                    width: s.width || 512,
                    height: s.height || 768,
                    negative_prompt: s.negative_prompt,
                    steps: s.steps,
                    cfg_scale: s.cfg_scale,
                    sampler_name: s.sampler_name,
                    seed: s.seed,
                    clip_skip: s.clip_skip,
                    context_tags: s.context_tags,
                  })),
                });
                console.log("[StyleProfileModal] ✅ Storyboard updated with profile ID:", profile.id);
                showToast("스토리보드 업데이트 완료", "success");
              } catch (err) {
                console.error("[StyleProfileModal] ❌ Failed to update storyboard:", err);
                showToast("스토리보드 업데이트 실패", "error");
              }
            } else {
              // 새 스토리보드 (씬이 없어도 프로필 정보는 저장)
              try {
                const res = await axios.post(`${API_BASE}/storyboards`, {
                  title: topic || "Draft Storyboard",
                  description: topic || "Style profile selected",
                  default_character_id: selectedCharacterId,
                  default_style_profile_id: profile.id,
                  scenes: scenes.map((s, i) => ({
                    scene_id: i,
                    script: s.script,
                    speaker: s.speaker,
                    duration: s.duration,
                    image_prompt: s.image_prompt,
                    image_prompt_ko: s.image_prompt_ko,
                    image_url: s.image_url,
                    description: s.description,
                    width: s.width || 512,
                    height: s.height || 768,
                    negative_prompt: s.negative_prompt,
                    steps: s.steps,
                    cfg_scale: s.cfg_scale,
                    sampler_name: s.sampler_name,
                    seed: s.seed,
                    clip_skip: s.clip_skip,
                    context_tags: s.context_tags,
                  })),
                });
                setMeta({ storyboardId: res.data.storyboard_id });
                console.log("[StyleProfileModal] ✅ Storyboard created with ID:", res.data.storyboard_id, "profile ID:", profile.id);
                showToast("스토리보드 생성 완료", "success");
              } catch (err) {
                console.error("[StyleProfileModal] ❌ Failed to create storyboard:", err);
                showToast("스토리보드 생성 실패: " + (err as Error).message, "error");
              }
            }

            // SD Model 변경 (백그라운드)
            if (profile.sd_model_name) {
              axios
                .post(`${API_BASE}/sd/options`, {
                  sd_model_checkpoint: profile.sd_model_name,
                })
                .then(() => {
                  showToast(
                    `스타일 프로필 "${profile.display_name || profile.name}" 로드 완료\n` +
                    `Model: ${profile.sd_model_name}\n` +
                    `LoRAs: ${profile.loras?.length || 0}개\n` +
                    `Embeddings: ${(profile.negative_embeddings?.length || 0) + (profile.positive_embeddings?.length || 0)}개`,
                    "success"
                  );
                })
                .catch((err) => {
                  console.error("Failed to change SD model:", err);
                  showToast(
                    `프로필은 로드되었으나 Model 변경 실패: ${profile.sd_model_name}`,
                    "error"
                  );
                });
            } else {
              showToast(`스타일 프로필 "${profile.display_name || profile.name}"이(가) 선택되었습니다`, "success");
            }
          }}
          onSkip={() => {
            setShowStyleProfileModal(false);
            showToast("스타일 프로필 선택을 건너뛰었습니다", "success");
          }}
        />
      )}
    </div>
  );
}

export default function StudioPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      }
    >
      <StudioContent />
    </Suspense>
  );
}
