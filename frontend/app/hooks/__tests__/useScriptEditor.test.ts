import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";

// Bypass zustand persist (jsdom lacks proper localStorage)
vi.mock("zustand/middleware", async () => {
  const actual = await vi.importActual<typeof import("zustand/middleware")>("zustand/middleware");
  return {
    ...actual,
    persist: (fn: (...args: unknown[]) => unknown) => fn,
  };
});

import { useScriptEditor } from "../useScriptEditor";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import type { SceneItem } from "../useScriptEditor";

function makeScene(overrides?: Partial<SceneItem>): SceneItem {
  return {
    id: 1,
    client_id: "test-1",
    order: 1,
    script: "Hello",
    speaker: "Narrator",
    duration: 3,
    image_prompt: "",
    image_prompt_ko: "",
    image_url: null,
    ...overrides,
  };
}

describe("useScriptEditor — dirty tracking & unmount sync", () => {
  beforeEach(() => {
    useStoryboardStore.getState().reset();
  });

  // ─── setField dirty tracking ───

  it("marks global store isDirty when topic changes", () => {
    const { result } = renderHook(() => useScriptEditor());

    act(() => result.current.setField("topic", "New Topic"));

    expect(useStoryboardStore.getState().isDirty).toBe(true);
  });

  it("marks global store isDirty when description changes", () => {
    const { result } = renderHook(() => useScriptEditor());

    act(() => result.current.setField("description", "Some description"));

    expect(useStoryboardStore.getState().isDirty).toBe(true);
  });

  it.each([
    ["duration", 60],
    ["language", "English"],
    ["structure", "Dialogue"],
    ["characterId", 42],
    ["characterName", "Alice"],
    ["references", "https://example.com"],
    ["preset", "cinematic"],
  ] as const)("marks isDirty for content field: %s", (key, value) => {
    const { result } = renderHook(() => useScriptEditor());

    act(() => result.current.setField(key, value as never));

    expect(useStoryboardStore.getState().isDirty).toBe(true);
  });

  it("does NOT mark isDirty for non-content field: isGenerating", () => {
    const { result } = renderHook(() => useScriptEditor());

    act(() => result.current.setField("isGenerating", true));

    expect(useStoryboardStore.getState().isDirty).toBe(false);
  });

  it("does NOT mark isDirty for non-content field: progress", () => {
    const { result } = renderHook(() => useScriptEditor());

    act(() => result.current.setField("progress", { node: "x", label: "x", percent: 50 }));

    expect(useStoryboardStore.getState().isDirty).toBe(false);
  });

  // ─── updateScene dirty tracking ───

  it("marks global store isDirty when scene is updated", () => {
    const { result } = renderHook(() => useScriptEditor());

    act(() => result.current.setField("scenes", [makeScene()]));
    useStoryboardStore.getState().set({ isDirty: false });

    act(() => result.current.updateScene(0, { script: "Updated" }));

    expect(useStoryboardStore.getState().isDirty).toBe(true);
  });

  // ─── unmount sync ───

  it("syncs topic to global store on unmount when dirty", () => {
    const { result, unmount } = renderHook(() => useScriptEditor());

    act(() => result.current.setField("topic", "Unmount Topic"));

    unmount();

    expect(useStoryboardStore.getState().topic).toBe("Unmount Topic");
  });

  it("syncs multiple fields to global store on unmount", () => {
    const { result, unmount } = renderHook(() => useScriptEditor());

    act(() => {
      result.current.setField("topic", "My Topic");
      result.current.setField("language", "English");
      result.current.setField("duration", 60);
    });

    unmount();

    const store = useStoryboardStore.getState();
    expect(store.topic).toBe("My Topic");
    expect(store.language).toBe("English");
    expect(store.duration).toBe(60);
  });

  it("syncs scenes to global store on unmount when scenes edited", () => {
    const { result, unmount } = renderHook(() => useScriptEditor());

    act(() => {
      result.current.setField("topic", "Topic");
      result.current.setField("scenes", [makeScene({ script: "Scene 1" })]);
    });
    act(() => result.current.updateScene(0, { script: "Scene 1 edited" }));

    unmount();

    const scenes = useStoryboardStore.getState().scenes;
    expect(scenes).toHaveLength(1);
    expect(scenes[0].script).toBe("Scene 1 edited");
  });

  it("does NOT sync on unmount when not dirty", () => {
    useStoryboardStore.getState().set({ topic: "Original" });

    const { unmount } = renderHook(() => useScriptEditor());

    unmount();

    expect(useStoryboardStore.getState().topic).toBe("Original");
  });

  it("does NOT sync on unmount when topic is empty and no scenes", () => {
    useStoryboardStore.getState().set({ topic: "Original" });

    const { result, unmount } = renderHook(() => useScriptEditor());

    act(() => result.current.setField("language", "English"));

    unmount();

    // topic is empty and scenes is empty → skip sync
    expect(useStoryboardStore.getState().topic).toBe("Original");
  });

  // ─── reset clears dirty ───

  it("reset clears dirty so unmount does not sync", () => {
    useStoryboardStore.getState().set({ topic: "Before" });

    const { result, unmount } = renderHook(() => useScriptEditor());

    act(() => result.current.setField("topic", "Changed"));
    act(() => result.current.reset());

    unmount();

    expect(useStoryboardStore.getState().topic).toBe("Before");
  });
});
