import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { ProjectItem, GroupItem } from "../types";

export interface ContextState {
  // Persisted
  projectId: number | null;
  groupId: number | null;
  storyboardId: number | null;
  storyboardTitle: string;

  // Transient (re-fetched on mount)
  projects: ProjectItem[];
  groups: GroupItem[];
  isLoadingProjects: boolean;
  isLoadingGroups: boolean;

  // Actions
  setContext: (
    updates: Partial<
      Pick<ContextState, "projectId" | "groupId" | "storyboardId" | "storyboardTitle">
    >
  ) => void;
  setProjects: (projects: ProjectItem[]) => void;
  setGroups: (groups: GroupItem[]) => void;
  setContextLoading: (
    updates: Partial<Pick<ContextState, "isLoadingProjects" | "isLoadingGroups">>
  ) => void;
  resetContext: () => void;
}

const CONTEXT_STORE_KEY = "shorts-producer:context:v1";

const TRANSIENT_CONTEXT_KEYS: (keyof ContextState)[] = [
  "projects",
  "groups",
  "isLoadingProjects",
  "isLoadingGroups",
];

export const useContextStore = create<ContextState>()(
  persist(
    (set) => ({
      projectId: null,
      groupId: null,
      storyboardId: null,
      storyboardTitle: "",
      projects: [],
      groups: [],
      isLoadingProjects: false,
      isLoadingGroups: false,

      setContext: (updates) => set((s) => ({ ...s, ...updates })),
      setProjects: (projects) => set({ projects }),
      setGroups: (groups) => set({ groups }),
      setContextLoading: (updates) => set((s) => ({ ...s, ...updates })),
      resetContext: () => set({ storyboardId: null, storyboardTitle: "" }),
    }),
    {
      name: CONTEXT_STORE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => {
        const persisted: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(state)) {
          if (typeof value === "function") continue;
          if (TRANSIENT_CONTEXT_KEYS.includes(key as keyof ContextState)) continue;
          persisted[key] = value;
        }
        return persisted as Partial<ContextState>;
      },
    }
  )
);
