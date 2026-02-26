import type { Scene } from "../types";

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
 */
export function buildScenesPayload(scenes: Scene[]) {
  return scenes.map((s, i) => ({
    scene_id: i,
    client_id: s.client_id,
    script: s.script,
    speaker: s.speaker,
    duration: s.duration,
    image_prompt: s.image_prompt,
    image_prompt_ko: s.image_prompt_ko,

    width: s.width || 512,
    height: s.height || 768,
    negative_prompt: s.negative_prompt,
    context_tags: s.context_tags,
    character_actions: s.character_actions || undefined,
    image_asset_id: s.image_asset_id ?? null,
    environment_reference_id: s.environment_reference_id ?? null,
    environment_reference_weight: s.environment_reference_weight ?? 0.3,
    use_reference_only: s.use_reference_only ?? true,
    reference_only_weight: s.reference_only_weight ?? 0.5,
    candidates: sanitizeCandidatesForDb(s.candidates),
    // Per-scene generation settings override
    use_controlnet: s.use_controlnet ?? null,
    controlnet_weight: s.controlnet_weight ?? null,
    use_ip_adapter: s.use_ip_adapter ?? null,
    ip_adapter_reference: s.ip_adapter_reference ?? null,
    ip_adapter_weight: s.ip_adapter_weight ?? null,
    multi_gen_enabled: s.multi_gen_enabled ?? null,
    controlnet_pose: s.controlnet_pose ?? null,
    voice_design_prompt: s.voice_design_prompt ?? null,
    head_padding: s.head_padding ?? null,
    tail_padding: s.tail_padding ?? null,
  }));
}
