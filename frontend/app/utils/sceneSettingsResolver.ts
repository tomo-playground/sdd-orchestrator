/**
 * Per-scene generation settings resolver.
 * Scene override ?? Global default fallback.
 *
 * Narrator guard is NOT applied here — it's handled at generation time.
 */
import type { Scene } from "../types";
import { resolveIpAdapterForSpeaker, type IpAdapterResolverState } from "./speakerResolver";

type GlobalControlnetState = {
  useControlnet: boolean;
  controlnetWeight: number;
};

type GlobalIpAdapterState = IpAdapterResolverState & {
  useIpAdapter: boolean;
};

type GlobalMultiGenState = {
  multiGenEnabled: boolean;
};

export type ResolvedControlnet = {
  enabled: boolean;
  weight: number;
};

export type ResolvedIpAdapter = {
  enabled: boolean;
  reference: string;
  weight: number;
};

/** Resolve ControlNet settings: scene override ?? global */
export function resolveSceneControlnet(
  scene: Scene,
  global: GlobalControlnetState
): ResolvedControlnet {
  return {
    enabled: scene.use_controlnet ?? global.useControlnet,
    weight: scene.controlnet_weight ?? global.controlnetWeight,
  };
}

/** Resolve IP-Adapter settings: scene override ?? global (with speaker B fallback) */
export function resolveSceneIpAdapter(
  scene: Scene,
  global: GlobalIpAdapterState
): ResolvedIpAdapter {
  const speakerFallback = resolveIpAdapterForSpeaker(scene.speaker, global);

  return {
    enabled: scene.use_ip_adapter ?? global.useIpAdapter,
    reference: scene.ip_adapter_reference ?? speakerFallback.reference,
    weight: scene.ip_adapter_weight ?? speakerFallback.weight,
  };
}

/** Resolve multi-gen (3x candidates) setting: scene override ?? global */
export function resolveSceneMultiGen(
  scene: Scene,
  global: GlobalMultiGenState
): boolean {
  return scene.multi_gen_enabled ?? global.multiGenEnabled;
}
