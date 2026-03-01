import { describe, it, expect, vi, beforeEach } from "vitest";

// Zustand v5 persist requires localStorage mock before import
vi.hoisted(() => {
  const store: Record<string, string> = {};
  const mock = {
    store,
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      for (const k of Object.keys(store)) delete store[k];
    },
    key: () => null,
    length: 0,
  };
  globalThis.localStorage = mock as unknown as Storage;
});

import { useContextStore } from "../useContextStore";

describe("useContextStore", () => {
  beforeEach(() => {
    useContextStore.setState({
      projectId: null,
      groupId: null,
      storyboardId: null,
      storyboardTitle: "",
      projects: [],
      groups: [],
      isLoadingProjects: false,
      isLoadingGroups: false,
      effectivePresetName: null,
      effectivePresetSource: null,
      effectiveStyleProfileId: null,
      effectiveCharacterId: null,
      effectiveConfigLoaded: false,
    });
  });

  describe("setContext", () => {
    it("updates projectId", () => {
      useContextStore.getState().setContext({ projectId: 1 });
      expect(useContextStore.getState().projectId).toBe(1);
    });

    it("updates multiple fields at once", () => {
      useContextStore.getState().setContext({
        storyboardId: 42,
        storyboardTitle: "My Story",
      });
      expect(useContextStore.getState().storyboardId).toBe(42);
      expect(useContextStore.getState().storyboardTitle).toBe("My Story");
    });

    it("preserves unchanged fields", () => {
      useContextStore.getState().setContext({ projectId: 1 });
      useContextStore.getState().setContext({ groupId: 2 });
      expect(useContextStore.getState().projectId).toBe(1);
      expect(useContextStore.getState().groupId).toBe(2);
    });
  });

  describe("setProjects", () => {
    it("sets projects array", () => {
      const projects = [{ id: 1, name: "P1" }];
      useContextStore.getState().setProjects(projects as never);
      expect(useContextStore.getState().projects).toEqual(projects);
    });
  });

  describe("setGroups", () => {
    it("sets groups array", () => {
      const groups = [{ id: 1, name: "G1" }];
      useContextStore.getState().setGroups(groups as never);
      expect(useContextStore.getState().groups).toEqual(groups);
    });
  });

  describe("setContextLoading", () => {
    it("sets loading flags", () => {
      useContextStore.getState().setContextLoading({ isLoadingProjects: true });
      expect(useContextStore.getState().isLoadingProjects).toBe(true);
    });
  });

  describe("setEffectivePreset", () => {
    it("sets preset name and source", () => {
      useContextStore.getState().setEffectivePreset("Post Standard", "group");
      expect(useContextStore.getState().effectivePresetName).toBe("Post Standard");
      expect(useContextStore.getState().effectivePresetSource).toBe("group");
    });

    it("clears preset when null", () => {
      useContextStore.getState().setEffectivePreset("test", "group");
      useContextStore.getState().setEffectivePreset(null, null);
      expect(useContextStore.getState().effectivePresetName).toBeNull();
      expect(useContextStore.getState().effectivePresetSource).toBeNull();
    });
  });

  describe("setEffectiveDefaults", () => {
    it("sets style profile ID and character ID", () => {
      useContextStore.getState().setEffectiveDefaults(3, 5, true);
      expect(useContextStore.getState().effectiveStyleProfileId).toBe(3);
      expect(useContextStore.getState().effectiveCharacterId).toBe(5);
      expect(useContextStore.getState().effectiveConfigLoaded).toBe(true);
    });
  });

  describe("resetContext", () => {
    it("resets storyboard-related fields", () => {
      useContextStore.getState().setContext({ storyboardId: 42, storyboardTitle: "Test" });
      useContextStore.getState().setEffectivePreset("name", "group");
      useContextStore.getState().setEffectiveDefaults(3, 5, true);

      useContextStore.getState().resetContext();

      expect(useContextStore.getState().storyboardId).toBeNull();
      expect(useContextStore.getState().storyboardTitle).toBe("");
      expect(useContextStore.getState().effectivePresetName).toBeNull();
      expect(useContextStore.getState().effectiveStyleProfileId).toBeNull();
      expect(useContextStore.getState().effectiveConfigLoaded).toBe(false);
    });

    it("preserves projectId and groupId", () => {
      useContextStore.getState().setContext({ projectId: 1, groupId: 2 });
      useContextStore.getState().resetContext();

      expect(useContextStore.getState().projectId).toBe(1);
      expect(useContextStore.getState().groupId).toBe(2);
    });
  });
});
