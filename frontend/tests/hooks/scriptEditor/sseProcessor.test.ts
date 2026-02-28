// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { ScriptStreamEvent } from "../../../app/types";

// Mock stores
const mockStoryboardSet = vi.fn();
const mockRenderSet = vi.fn();

vi.mock("../../../app/store/useStoryboardStore", () => ({
  useStoryboardStore: Object.assign(vi.fn(), {
    getState: () => ({ set: mockStoryboardSet }),
  }),
}));
vi.mock("../../../app/store/useRenderStore", () => ({
  useRenderStore: Object.assign(vi.fn(), {
    getState: () => ({ set: mockRenderSet }),
  }),
}));
vi.mock("../../../app/utils/pipelineSteps", () => ({
  updatePipelineSteps: vi.fn((_steps) => []),
}));
vi.mock("../../../app/hooks/scriptEditor/mappers", () => ({
  mapEventScenes: vi.fn((scenes) => scenes.map((s: { id?: number }) => ({ ...s, client_id: "c" }))),
}));

import { parseSSEStream } from "../../../app/hooks/scriptEditor/sseProcessor";

function makeSSEResponse(events: string[]): Response {
  const text = events.join("");
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(text));
      controller.close();
    },
  });
  return { body: stream } as unknown as Response;
}

describe("parseSSEStream", () => {
  it("parses SSE events separated by double newlines", async () => {
    const events: ScriptStreamEvent[] = [];
    const event1: ScriptStreamEvent = {
      node: "research",
      label: "Research",
      percent: 10,
      status: "running",
    };
    const event2: ScriptStreamEvent = {
      node: "writer",
      label: "Writer",
      percent: 40,
      status: "running",
    };
    const response = makeSSEResponse([
      `data: ${JSON.stringify(event1)}\n\n`,
      `data: ${JSON.stringify(event2)}\n\n`,
    ]);

    await parseSSEStream(response, (e) => events.push(e));

    expect(events).toHaveLength(2);
    expect(events[0].node).toBe("research");
    expect(events[1].node).toBe("writer");
  });

  it("handles chunked data across multiple reads", async () => {
    const events: ScriptStreamEvent[] = [];
    const fullEvent = `data: ${JSON.stringify({ node: "a", label: "A", percent: 1, status: "running" })}\n\n`;
    const mid = Math.floor(fullEvent.length / 2);
    const chunk1 = fullEvent.slice(0, mid);
    const chunk2 = fullEvent.slice(mid);

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(chunk1));
        controller.enqueue(encoder.encode(chunk2));
        controller.close();
      },
    });
    const response = { body: stream } as unknown as Response;

    await parseSSEStream(response, (e) => events.push(e));
    expect(events).toHaveLength(1);
    expect(events[0].node).toBe("a");
  });

  it("skips malformed JSON gracefully", async () => {
    const events: ScriptStreamEvent[] = [];
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const validEvent = `data: ${JSON.stringify({ node: "b", label: "B", percent: 2, status: "running" })}\n\n`;
    const response = makeSSEResponse(["data: {broken json\n\n", validEvent]);

    await parseSSEStream(response, (e) => events.push(e));

    expect(events).toHaveLength(1);
    expect(events[0].node).toBe("b");
    expect(warnSpy).toHaveBeenCalledWith(
      "[SSE] malformed event skipped:",
      expect.stringContaining("broken")
    );
    warnSpy.mockRestore();
  });

  it("ignores non-data lines", async () => {
    const events: ScriptStreamEvent[] = [];
    const validEvent = `data: ${JSON.stringify({ node: "c", label: "C", percent: 3, status: "running" })}\n\n`;
    const response = makeSSEResponse([": comment\n\n", validEvent]);

    await parseSSEStream(response, (e) => events.push(e));
    expect(events).toHaveLength(1);
  });

  it("throws when response.body is null", async () => {
    const response = { body: null } as unknown as Response;
    await expect(parseSSEStream(response, vi.fn())).rejects.toThrow("streaming not supported");
  });
});

describe("casting recommendation from SSE", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("stores casting recommendation on inventory_resolve event", async () => {
    const { processSSEStream } = await import("../../../app/hooks/scriptEditor/sseProcessor");

    const event: ScriptStreamEvent = {
      node: "inventory_resolve",
      label: "Inventory",
      percent: 4,
      status: "running",
      node_result: {
        character_id: 1,
        character_name: "Alice",
        character_b_id: 2,
        character_b_name: "Bob",
        structure: "Dialogue",
        style_profile_id: 10,
        reasoning: "Best fit for topic",
      },
    };
    const response = makeSSEResponse([`data: ${JSON.stringify(event)}\n\n`]);
    const setState = vi.fn();

    await processSSEStream(response, setState);

    expect(mockStoryboardSet).toHaveBeenCalledWith({
      castingRecommendation: {
        character_id: 1,
        character_name: "Alice",
        character_b_id: 2,
        character_b_name: "Bob",
        structure: "Dialogue",
        style_profile_id: 10,
        reasoning: "Best fit for topic",
      },
    });
  });

  it("skips casting if character_name is not a string", async () => {
    const { processSSEStream } = await import("../../../app/hooks/scriptEditor/sseProcessor");

    const event: ScriptStreamEvent = {
      node: "inventory_resolve",
      label: "Inventory",
      percent: 4,
      status: "running",
      node_result: { character_id: 1 }, // no character_name
    };
    const response = makeSSEResponse([`data: ${JSON.stringify(event)}\n\n`]);
    const setState = vi.fn();

    await processSSEStream(response, setState);

    expect(mockStoryboardSet).not.toHaveBeenCalled();
  });
});

describe("processSSEStream integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns finalScenes on completed event", async () => {
    const { processSSEStream } = await import("../../../app/hooks/scriptEditor/sseProcessor");

    const event = {
      node: "director",
      label: "Director",
      percent: 100,
      status: "completed",
      result: { scenes: [{ id: 1, script: "Hello" }] },
    } as unknown as ScriptStreamEvent;
    const response = makeSSEResponse([`data: ${JSON.stringify(event)}\n\n`]);
    const setState = vi.fn();

    const result = await processSSEStream(response, setState);

    expect(result.finalScenes).toHaveLength(1);
    expect(result.isWaiting).toBe(false);
  });

  it("returns isWaiting on waiting_for_input event", async () => {
    const { processSSEStream } = await import("../../../app/hooks/scriptEditor/sseProcessor");

    const event = {
      node: "human_gate",
      label: "Review",
      percent: 80,
      status: "waiting_for_input",
      result: { scenes: [{ id: 1, script: "Draft" }] },
    } as unknown as ScriptStreamEvent;
    const response = makeSSEResponse([`data: ${JSON.stringify(event)}\n\n`]);
    const setState = vi.fn();

    const result = await processSSEStream(response, setState);

    expect(result.isWaiting).toBe(true);
  });

  it("throws on error event", async () => {
    const { processSSEStream } = await import("../../../app/hooks/scriptEditor/sseProcessor");

    const event: ScriptStreamEvent = {
      node: "error",
      label: "Error",
      percent: 0,
      status: "error",
      error: "Pipeline exploded",
    };
    const response = makeSSEResponse([`data: ${JSON.stringify(event)}\n\n`]);
    const setState = vi.fn();

    await expect(processSSEStream(response, setState)).rejects.toThrow("Pipeline exploded");
  });

  it("tracks threadId when option is set", async () => {
    const { processSSEStream } = await import("../../../app/hooks/scriptEditor/sseProcessor");

    const event: ScriptStreamEvent = {
      node: "research",
      label: "Research",
      percent: 10,
      status: "running",
      thread_id: "thread-abc",
    };
    const response = makeSSEResponse([`data: ${JSON.stringify(event)}\n\n`]);
    const setState = vi.fn();

    await processSSEStream(response, setState, { trackThreadId: true });

    // setState is called per event; verify thread_id is passed through
    expect(setState).toHaveBeenCalled();
    const updater = setState.mock.calls[0][0];
    const prev = { threadId: null, pipelineSteps: [], directorSkipStages: [], nodeResults: {} };
    const next = updater(prev);
    expect(next.threadId).toBe("thread-abc");
  });

  it("populates renderStore on sound_recommendation", async () => {
    const { processSSEStream } = await import("../../../app/hooks/scriptEditor/sseProcessor");

    const event = {
      node: "director",
      label: "Director",
      percent: 100,
      status: "completed",
      result: {
        scenes: [{ id: 1, script: "Hello" }],
        sound_recommendation: { prompt: "epic orchestral", mood: "dramatic" },
      },
    } as unknown as ScriptStreamEvent;
    const response = makeSSEResponse([`data: ${JSON.stringify(event)}\n\n`]);
    const setState = vi.fn();

    await processSSEStream(response, setState);

    expect(mockRenderSet).toHaveBeenCalledWith({
      bgmPrompt: "epic orchestral",
      bgmMood: "dramatic",
      bgmMode: "auto",
    });
  });
});
