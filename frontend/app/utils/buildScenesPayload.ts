import type { Scene } from "../types";
import { DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT } from "../constants";

/**
 * Sanitize candidates for DB storage.
 * Removes image_url (stored via media_asset_id, backend resolves URL on GET)
 */
export function sanitizeCandidatesForDb(candidates: Scene["candidates"]): Array<{
  media_asset_id: number;
  match_rate?: number;
  adjusted_match_rate?: number;
  identity_score?: number;
}> | null {
  if (!candidates || candidates.length === 0) return null;
  return candidates.map((c) => ({
    media_asset_id: c.media_asset_id,
    ...(c.match_rate !== undefined && { match_rate: c.match_rate }),
    ...(c.adjusted_match_rate !== undefined && { adjusted_match_rate: c.adjusted_match_rate }),
    ...(c.identity_score !== undefined && { identity_score: c.identity_score }),
  }));
}

/**
 * Map Scene[] to API payload format for storyboard save/update.
 * Single source of truth — used by autoSave, persist, and styleProfile flows.
 * Spread passthrough: UI-only 필드를 제거하고 나머지를 그대로 전달.
 * 신규 필드 추가 시 매핑 누락으로 인한 데이터 소실 방지.
 *
 * tts_asset_id: SCENE_TRANSIENT_FIELDS에 포함돼 autoSave를 트리거하지 않지만,
 * 이 함수의 ...rest 스프레드에는 의도적으로 포함된다. TTS Prebuild API가 DB에
 * 직접 저장하므로 autoSave 중복은 불필요하나, 명시적 저장(saveStoryboard) 시에는
 * 최신 tts_asset_id가 payload에 포함되어야 한다.
 */
export function buildScenesPayload(scenes: Scene[]) {
  return scenes.map((s, i) => {
    // Destructure out UI-only fields that should not be sent to API
    const {
      id: _id,
      order: _order,
      isGenerating: _isGenerating,
      debug_payload: _debugPayload,
      debug_prompt: _debugPrompt,
      _auto_pin_previous,
      activity_log_id: _activityLogId,
      negative_prompt_extra: _negativePromptExtra,
      image_url: _imageUrl,
      candidates: _candidates,
      ...rest
    } = s;

    return {
      ...rest,
      // API-specific overrides
      scene_id: i,
      // Backend SSOT fallback: /presets API image_defaults
      width: s.width || DEFAULT_IMAGE_WIDTH,
      height: s.height || DEFAULT_IMAGE_HEIGHT,
      candidates: sanitizeCandidatesForDb(s.candidates),
    };
  });
}
