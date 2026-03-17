import axios from "axios";
import type { Scene, ImageValidation } from "../../types";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { API_BASE, ADMIN_API_BASE } from "../../constants";

/** Store a base64 image on the backend and return URL + asset_id */
export async function storeSceneImage(
  dataUrl: string,
  projectId: number,
  groupId: number,
  storyboardId: number,
  sceneId: number,
  fileName?: string,
  clientId?: string
): Promise<{ url: string; asset_id?: number }> {
  if (!dataUrl || !dataUrl.startsWith("data:")) return { url: dataUrl };
  try {
    const res = await fetch(`${API_BASE}/image/store`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_b64: dataUrl,
        project_id: projectId,
        group_id: groupId,
        storyboard_id: storyboardId,
        scene_id: sceneId,
        client_id: clientId || undefined,
        file_name: fileName,
      }),
    });
    if (!res.ok) return { url: dataUrl };
    const data = await res.json();
    return {
      url: (data?.url as string) ?? dataUrl,
      asset_id: data?.asset_id as number | undefined,
    };
  } catch {
    return { url: dataUrl };
  }
}

export async function validateImageCandidate(
  imageUrl: string,
  prompt: string,
  sceneId?: number,
  characterId?: number | null
) {
  if (!imageUrl || imageUrl.startsWith("data:")) return null;
  try {
    const { storyboardId } = useContextStore.getState();
    const base =
      imageUrl.startsWith("http://") || imageUrl.startsWith("https://")
        ? { image_url: imageUrl }
        : { image_b64: imageUrl };
    const payload = {
      ...base,
      prompt,
      storyboard_id: storyboardId,
      scene_id: sceneId,
      ...(characterId ? { character_id: characterId } : {}),
    };
    const res = await axios.post(`${API_BASE}/scene/validate-and-auto-edit`, payload);
    return res.data;
  } catch {
    return null;
  }
}

export type ProcessOpts = {
  images: string[];
  scene: Scene;
  prompt: string;
  usedPrompt?: string;
  warnings?: string[];
  selectedCharacterId: number | null;
  silent: boolean;
  controlnet_pose?: string;
  ip_adapter_reference?: string;
  preStored?: { url: string; asset_id: number };
  /** SSE 응답에 포함된 validation 결과 — 있으면 별도 API 호출 생략 */
  sseValidation?: {
    match_rate?: number;
    matched_tags?: string[];
    missing_tags?: string[];
  };
};

/** Store, validate, and rank generated images (shared by SSE and sync paths) */
export async function processGeneratedImages(opts: ProcessOpts): Promise<Partial<Scene> | null> {
  const { images, scene, prompt, usedPrompt, warnings = [], selectedCharacterId, silent } = opts;
  const { showToast } = useUIStore.getState();
  const { projectId, groupId, storyboardId: currentId } = useContextStore.getState();

  if (!silent && warnings.length > 0) {
    warnings.forEach((msg: string) => showToast(msg, "success"));
  }

  if (!projectId || !groupId || !currentId) {
    if (!silent) showToast("채널/시리즈를 먼저 선택하세요", "error");
    return null;
  }

  // Re-resolve current DB scene_id from stable client_id (DB id may change during save)
  const currentScene = useStoryboardStore
    .getState()
    .scenes.find((s) => s.client_id === scene.client_id);
  const sceneDbId = currentScene?.id ?? scene.id;

  const storedResults = opts.preStored
    ? [{ url: opts.preStored.url, asset_id: opts.preStored.asset_id }]
    : await Promise.all(
        images.map((b64: string, idx: number) => {
          const dataUrl = `data:image/png;base64,${b64}`;
          return storeSceneImage(
            dataUrl,
            projectId,
            groupId,
            currentId,
            sceneDbId,
            `scene_${sceneDbId}_${Date.now()}_${idx}.png`,
            scene.client_id
          );
        })
      );

  // SSE validation 결과가 있으면 별도 API 호출 생략 (preStored 여부와 무관)
  const useSseValidation = opts.sseValidation != null;

  const validationResults = await Promise.all(
    storedResults.map(async (stored) => {
      let vResult: ImageValidation | null | undefined;

      if (useSseValidation) {
        // SSE validation 결과를 ImageValidation 형태로 변환
        const sv = opts.sseValidation!;
        vResult = {
          match_rate: sv.match_rate ?? 0,
          matched: sv.matched_tags ?? [],
          missing: sv.missing_tags ?? [],
          extra: [],
        };
      } else {
        const validation = await validateImageCandidate(
          stored.url,
          prompt,
          sceneDbId,
          selectedCharacterId
        );
        vResult = validation?.validation_result ?? validation;
      }

      return {
        image_url: stored.url,
        asset_id: stored.asset_id,
        match_rate: typeof vResult?.match_rate === "number" ? vResult.match_rate : 0,
        adjusted_match_rate:
          typeof vResult?.adjusted_match_rate === "number"
            ? vResult.adjusted_match_rate
            : undefined,
        identity_score:
          typeof vResult?.identity_score === "number" ? vResult.identity_score : undefined,
        validation: vResult,
      };
    })
  );

  // Sort: identity_score first, then adjusted_match_rate fallback to match_rate
  const sortedCandidates = validationResults.sort((a, b) => {
    const idA = a.identity_score ?? -1;
    const idB = b.identity_score ?? -1;
    if (idA !== idB) return idB - idA;
    return (
      (b.adjusted_match_rate ?? b.match_rate ?? 0) - (a.adjusted_match_rate ?? a.match_rate ?? 0)
    );
  });
  const bestCandidate = sortedCandidates[0];
  const candidates = sortedCandidates
    .filter((c): c is typeof c & { asset_id: number } => c.asset_id != null)
    .map((c) => ({
      media_asset_id: c.asset_id,
      match_rate: c.match_rate ?? undefined,
      adjusted_match_rate: c.adjusted_match_rate,
      identity_score: c.identity_score,
      image_url: c.image_url,
    }));

  if (bestCandidate.validation) {
    const { imageValidationResults } = useStoryboardStore.getState();
    useStoryboardStore.getState().set({
      imageValidationResults: {
        ...imageValidationResults,
        [scene.client_id]: bestCandidate.validation,
      },
    });
  }

  let activityLogId: number | undefined;
  try {
    const currentStoryboardId = useContextStore.getState().storyboardId;
    if (currentStoryboardId) {
      // Re-resolve again in case another save happened during store/validate
      const latestScene = useStoryboardStore
        .getState()
        .scenes.find((s) => s.client_id === scene.client_id);
      const logSceneId = latestScene?.id ?? sceneDbId;
      const logRes = await axios.post(`${ADMIN_API_BASE}/activity-logs`, {
        storyboard_id: currentStoryboardId,
        scene_id: logSceneId,
        client_id: scene.client_id,
        character_id: selectedCharacterId || undefined,
        prompt,
        negative_prompt: undefined,
        tags: prompt.split(",").map((t: string) => t.trim()),
        sd_params: {},
        seed: -1,
        status: "pending",
        image_url: bestCandidate.image_url?.startsWith("data:")
          ? null
          : (bestCandidate.image_url ?? null),
        match_rate: bestCandidate.match_rate || null,
      });
      activityLogId = logRes.data.id;
    }
  } catch {
    // non-critical
  }

  return {
    image_url: bestCandidate.image_url,
    image_asset_id: bestCandidate.asset_id ?? null,
    candidates,
    image_prompt: usedPrompt || undefined,
    activity_log_id: activityLogId,
    use_controlnet: opts.controlnet_pose ? true : undefined,
    ip_adapter_reference: opts.ip_adapter_reference || undefined,
  } as Partial<Scene>;
}
