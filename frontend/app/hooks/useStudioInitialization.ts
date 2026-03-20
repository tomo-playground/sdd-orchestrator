"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import axios from "axios";
import { resetAllStores } from "../store/resetAllStores";
import { useContextStore } from "../store/useContextStore";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useRenderStore } from "../store/useRenderStore";
import { useUIStore } from "../store/useUIStore";
import { loadStyleProfileFromId } from "../store/actions/styleProfileActions";
import { loadGroupDefaults } from "../store/actions/groupActions";
import type { Scene } from "../types";
import { API_BASE, DEFAULT_STRUCTURE } from "../constants";
import { generateSceneClientId } from "../utils/uuid";
import { isMultiCharStructure } from "../utils/structure";

/**
 * Handles all studio initialization logic:
 * - Store reset on ?new=true
 * - Storyboard loading from DB on ?id=X
 * - Prompt apply from localStorage
 * - Transient data clearing on storyboard ID change
 */
export function useStudioInitialization() {
  const searchParams = useSearchParams();
  const storyboardId = searchParams.get("id");
  const [isLoadingDb, setIsLoadingDb] = useState(false);
  const [loadedProfileId, setLoadedProfileId] = useState<number | null>(null);
  const [needsStyleProfile, setNeedsStyleProfile] = useState(false);

  const setContext = useContextStore((s) => s.setContext);
  const setScenes = useStoryboardStore((s) => s.setScenes);
  const setPlan = useStoryboardStore((s) => s.set);

  // Reset store for ?new=true (DB creation deferred to first save/generate)
  const newHandledRef = useRef(false);

  useEffect(() => {
    const isNewStoryboard = searchParams.get("new") === "true";
    if (!isNewStoryboard) {
      // After ?new=true URL cleanup, skip one re-render to preserve isNewStoryboardMode
      if (newHandledRef.current) {
        newHandledRef.current = false;
        return;
      }
      // Clear isNewStoryboardMode whenever not on ?new=true
      // (mount, ?id=X load, group switch, etc.) — prevents stale flag
      if (useUIStore.getState().isNewStoryboardMode) {
        useUIStore.getState().set({ isNewStoryboardMode: false });
      }
      return;
    }
    if (newHandledRef.current) return;
    newHandledRef.current = true;

    // Async IIFE to handle resetAllStores (now async)
    (async () => {
      await resetAllStores();
      // Set store flag before URL cleanup (URL-independent new mode)
      useUIStore.getState().set({ isNewStoryboardMode: true });

      const { effectiveCharacterId } = useContextStore.getState();
      if (effectiveCharacterId) {
        setPlan({ selectedCharacterId: effectiveCharacterId });
      }

      // Apply backend generation defaults and SSOT config to freshly reset store
      try {
        const res = await fetch(`${API_BASE}/presets`);
        const data = await res.json();
        if (data?.generation_defaults) {
          useStoryboardStore.getState().applyGenerationDefaults(data.generation_defaults);
        }
        if (Array.isArray(data?.fast_track_skip_stages) && data.fast_track_skip_stages.length > 0) {
          useStoryboardStore.getState().set({ fastTrackSkipStages: data.fast_track_skip_stages });
        }
        // Backend SSOT: Hi-Res defaults, image defaults, TTS engine
        if (data?.hi_res_defaults) {
          useStoryboardStore.getState().set({ hiResDefaults: data.hi_res_defaults });
        }
        if (data?.image_defaults) {
          useStoryboardStore.getState().set({ imageDefaults: data.image_defaults });
        }
        if (data?.tts_engine) {
          useRenderStore.getState().set({ ttsEngine: data.tts_engine });
        }
      } catch {
        // silent — initialState fallback values are used
      }

      // Clear URL params (prevents searchParams re-trigger)
      const url = new URL(window.location.href);
      url.searchParams.delete("new");
      url.searchParams.delete("id");
      window.history.replaceState({}, "", url.toString());
    })();
  }, [searchParams, setPlan]);

  // Sync Backend SSOT values (hi_res_defaults, image_defaults, tts_engine) on mount.
  // The ?new=true path also fetches /presets inline, but ?id=X does not — this
  // effect ensures SSOT values are always loaded regardless of entry path.
  // Double-fetch on ?new=true is harmless (idempotent set).
  useEffect(() => {
    fetch(`${API_BASE}/presets`)
      .then((res) => res.json())
      .then((data) => {
        if (data?.hi_res_defaults) {
          useStoryboardStore.getState().set({ hiResDefaults: data.hi_res_defaults });
        }
        if (data?.image_defaults) {
          useStoryboardStore.getState().set({ imageDefaults: data.image_defaults });
        }
        if (data?.tts_engine) {
          useRenderStore.getState().set({ ttsEngine: data.tts_engine });
        }
      })
      .catch(() => {
        // silent — fallback values in store are used
      });
  }, []);

  // Clear transient data when switching between storyboards (not on initial mount)
  const prevStoryboardIdRef = useRef<string | null>(null);
  useEffect(() => {
    if (
      storyboardId &&
      prevStoryboardIdRef.current &&
      prevStoryboardIdRef.current !== storyboardId
    ) {
      useRenderStore.getState().reset();
    }
    prevStoryboardIdRef.current = storyboardId;
  }, [storyboardId]);

  // Load storyboard from DB if ?id=X
  useEffect(() => {
    if (!storyboardId) return;
    const id = parseInt(storyboardId, 10);
    if (isNaN(id)) return;

    setIsLoadingDb(true); // eslint-disable-line react-hooks/set-state-in-effect
    axios
      .get(`${API_BASE}/storyboards/${id}`)
      .then((res) => {
        const data = res.data;
        // Sync groupId and projectId from storyboard response
        const groupId = data.group_id ?? null;
        const projectId = data.project_id ?? null;
        setContext({
          storyboardId: data.id,
          storyboardTitle: data.title,
          ...(groupId ? { groupId } : {}),
          ...(projectId ? { projectId } : {}),
        });
        // Restore video data from DB, mapping label to correct slot
        const recentVideos = (data.recent_videos || []).map(
          (v: { url: string; label?: string; created_at: number; render_history_id?: number }) => ({
            url: v.url,
            label: v.label,
            created_at: v.created_at,
            render_history_id: v.render_history_id,
          })
        );
        const latestFull = recentVideos.find((v: { label?: string }) => v.label === "full");
        const latestPost = recentVideos.find((v: { label?: string }) => v.label === "post");
        useRenderStore.getState().set({
          videoUrl: data.video_url || null,
          videoUrlFull: latestFull?.url || data.video_url || null,
          videoUrlPost: latestPost?.url || null,
          recentVideos,
          videoCaption: data.caption || "",
          ...(data.bgm_prompt ? { bgmPrompt: data.bgm_prompt, bgmMode: "auto" as const } : {}),
          ...(data.bgm_mood ? { bgmMood: data.bgm_mood } : {}),
        });
        const structure = data.structure || DEFAULT_STRUCTURE;
        const isMulti = isMultiCharStructure(structure);
        const charBId = isMulti ? data.character_b_id || null : null;
        setPlan({
          selectedCharacterId: data.character_id || null,
          selectedCharacterBId: charBId,
          // Non-Dialogue: 명시적으로 Character B 관련 필드 초기화 (stale 데이터 방지)
          ...(!isMulti && {
            selectedCharacterBName: null,
            basePromptB: "",
            baseNegativePromptB: "",
            characterBLoras: [],
          }),
          structure,
          topic: data.title || "",
          description: data.description || "",
          storyboardVersion: data.version ?? null,
          ...(data.duration != null && { duration: data.duration }),
          ...(data.language != null && { language: data.language }),
          castingRecommendation: data.casting_recommendation ?? null,
        });

        // Parallel load: character A, character B, style profile are independent
        const parallelLoads: Promise<unknown>[] = [];
        if (data.character_id) {
          parallelLoads.push(loadCharacterData(data.character_id, setPlan));
        }
        if (charBId) {
          parallelLoads.push(loadCharacterBData(charBId, setPlan));
        }
        if (data.style_profile_id) {
          setLoadedProfileId(data.style_profile_id);
          parallelLoads.push(
            loadStyleProfileFromId(data.style_profile_id, { skipHiResSync: true })
          );
        } else {
          setLoadedProfileId(null);
          setNeedsStyleProfile(true);
        }
        // Load group render defaults in parallel (independent of character/style)
        if (groupId) {
          parallelLoads.push(
            loadGroupDefaults(groupId, {
              skipStyleProfile: !!data.style_profile_id,
            })
          );
        }
        if (parallelLoads.length > 0) {
          void Promise.allSettled(parallelLoads);
        }

        const mapped = data.scenes?.length > 0 ? mapDbScenes(data.scenes) : null;
        if (mapped) {
          setScenes(mapped);
          // Quality scores 자동 로드 (match_rate 복원) — fire-and-forget
          void loadQualityScores(data.id, mapped);
        }

        // Video metadata: likes만 초기화 (caption/hashtag는 Publish 탭에서 lazy 로드)
        if (!useRenderStore.getState().videoLikesCount) {
          useRenderStore.getState().set({
            videoLikesCount: `${Math.floor(Math.random() * 50 + 10)}K`,
          });
        }
      })
      .catch(async (err) => {
        if (err?.response?.status === 404) {
          await resetAllStores();
          useUIStore.getState().showToast("삭제되었거나 존재하지 않는 스토리보드입니다.", "error");
          const url = new URL(window.location.href);
          url.searchParams.delete("id");
          window.history.replaceState({}, "", url.toString());
        } else {
          setContext({ storyboardId: null });
        }
      })
      .finally(() => setIsLoadingDb(false));
  }, [storyboardId, setContext, setPlan, setScenes]);

  return {
    isLoadingDb,
    loadedProfileId,
    loadStyleProfileFromId,
    storyboardId,
    needsStyleProfile,
  };
}

// --- Helper: Load character data (A or B) ---
type CharacterFieldMap = {
  loras: string;
  basePrompt: string;
  baseNegative: string;
};

const CHAR_A_FIELDS: CharacterFieldMap = {
  loras: "characterLoras",
  basePrompt: "basePromptA",
  baseNegative: "baseNegativePromptA",
};

const CHAR_B_FIELDS: CharacterFieldMap = {
  loras: "characterBLoras",
  basePrompt: "basePromptB",
  baseNegative: "baseNegativePromptB",
};

async function loadCharacterForRole(
  characterId: number,
  fields: CharacterFieldMap,
  setPlan: (updates: Record<string, unknown>) => void
) {
  try {
    const charRes = await axios.get(`${API_BASE}/characters/${characterId}`);
    const char = charRes.data;
    const nameField =
      fields.basePrompt === "basePromptA" ? "selectedCharacterName" : "selectedCharacterBName";
    const updates: Record<string, unknown> = {
      [fields.loras]: char.loras || [],
      [fields.basePrompt]: char.positive_prompt || "",
      [fields.baseNegative]: char.negative_prompt || "",
      [nameField]: char.name || null,
    };
    setPlan(updates);
  } catch (err) {
    console.error(`Failed to load character (${fields.basePrompt}):`, err);
  }
}

function loadCharacterData(
  characterId: number,
  setPlan: (updates: Record<string, unknown>) => void
) {
  return loadCharacterForRole(characterId, CHAR_A_FIELDS, setPlan);
}

function loadCharacterBData(
  characterId: number,
  setPlan: (updates: Record<string, unknown>) => void
) {
  return loadCharacterForRole(characterId, CHAR_B_FIELDS, setPlan);
}

// --- Helper: Load quality scores and restore imageValidationResults ---
async function loadQualityScores(storyboardId: number, scenes: Scene[]) {
  try {
    const res = await axios.get(`${API_BASE}/quality/summary/${storyboardId}`);
    const scores: Array<{
      scene_id: number;
      match_rate: number;
      matched_tags: string[];
      missing_tags: string[];
      extra_tags: string[];
      identity_score?: number;
    }> = res.data?.scores ?? [];

    if (!scores.length) return;

    // scene_id(DB) → client_id 매핑
    const sceneById = new Map(scenes.map((s) => [s.id, s.client_id]));

    const validationMap: Record<string, import("../types").ImageValidation> = {};
    for (const score of scores) {
      const clientId = sceneById.get(score.scene_id);
      if (!clientId) continue;
      validationMap[clientId] = {
        match_rate: score.match_rate,
        matched: score.matched_tags ?? [],
        missing: score.missing_tags ?? [],
        extra: score.extra_tags ?? [],
        identity_score: score.identity_score,
      };
    }

    if (Object.keys(validationMap).length > 0) {
      useStoryboardStore.getState().set({ imageValidationResults: validationMap });
    }
  } catch {
    // silent — match rates will show as '--' until user validates manually
  }
}

// --- Helper: Map DB scenes to frontend Scene type ---
// Spread passthrough: DB 필드를 그대로 전달하고, 변환/기본값이 필요한 필드만 오버라이드.
// 신규 필드 추가 시 매핑 누락으로 인한 데이터 소실 방지.
function mapDbScenes(dbScenes: Record<string, unknown>[]): Scene[] {
  return dbScenes.map((s, i) => ({
    ...(s as unknown as Scene),
    // Fallbacks for required fields
    id: (s.id as number) || i,
    client_id: (s.client_id as string) || generateSceneClientId(),
    order: (s.order as number) ?? (s.scene_id as number) ?? i,
    script: (s.script as string) || "",
    speaker: ((s.speaker as string) || "Narrator") as Scene["speaker"],
    duration: (s.duration as number) || 3,
    image_prompt: (s.image_prompt as string) || "",
    image_prompt_ko: (s.image_prompt_ko as string) || "",
    negative_prompt: (s.negative_prompt as string) || "",
    // UI-only fields (always reset)
    isGenerating: false,
    debug_payload: "",
    _auto_pin_previous: (s._auto_pin_previous as boolean) ?? false,
  }));
}
