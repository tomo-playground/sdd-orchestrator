import type { StageLocationStatus } from "../types";
import { useStoryboardStore } from "../store/useStoryboardStore";

/**
 * Stage locations를 store에 반영하고, 씬의 background_id를 동기화한다.
 * autopilotActions와 useStageLocations 양쪽에서 공통 사용.
 */
export function syncStageLocationsToStore(locations: StageLocationStatus[]): void {
  useStoryboardStore.getState().set({ stageLocations: locations });

  const bgMap = new Map<number, number | null>();
  for (const loc of locations) {
    for (const sid of loc.scene_ids) {
      bgMap.set(sid, loc.background_id);
    }
  }

  const store = useStoryboardStore.getState();
  let changed = false;
  const synced = store.scenes.map((s) => {
    const bgId = bgMap.get(s.id);
    if (bgId !== undefined) {
      if (s.background_id !== bgId) {
        changed = true;
        return { ...s, background_id: bgId };
      }
      return s;
    }
    if (s.background_id != null) {
      changed = true;
      return { ...s, background_id: null };
    }
    return s;
  });
  if (changed) store.setScenes(synced);
}
