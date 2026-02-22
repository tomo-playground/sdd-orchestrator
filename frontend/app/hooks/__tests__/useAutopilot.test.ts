import { renderHook, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useAutopilot } from "../useAutopilot";

describe("useAutopilot", () => {
  describe("Initial State", () => {
    it("should initialize with idle state", () => {
      const { result } = renderHook(() => useAutopilot());

      expect(result.current.autoRunState).toEqual({
        status: "idle",
        step: "idle",
        message: "",
      });
      expect(result.current.autoRunLog).toEqual([]);
      expect(result.current.isAutoRunning).toBe(false);
      expect(result.current.autoRunProgress).toBe(0);
    });
  });

  describe("pushLog", () => {
    it("should add log messages", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.pushLog("Test message 1");
        result.current.pushLog("Test message 2");
      });

      expect(result.current.autoRunLog).toEqual(["Test message 1", "Test message 2"]);
    });

    it("should limit logs to MAX_LOG_LINES (100)", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        // Add 150 log messages
        for (let i = 0; i < 150; i++) {
          result.current.pushLog(`Message ${i}`);
        }
      });

      expect(result.current.autoRunLog).toHaveLength(100);
      // Should keep last 100 messages (50-149)
      expect(result.current.autoRunLog[0]).toBe("Message 50");
      expect(result.current.autoRunLog[99]).toBe("Message 149");
    });
  });

  describe("setStep", () => {
    it("should update to running state with step info", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setStep("images", "Generating images...");
      });

      expect(result.current.autoRunState).toEqual({
        status: "running",
        step: "images",
        message: "Generating images...",
      });
      expect(result.current.isAutoRunning).toBe(true);
    });

    it("should handle all step types", () => {
      const { result } = renderHook(() => useAutopilot());
      const steps: Array<{
        id: "images" | "render";
        msg: string;
      }> = [
        { id: "images", msg: "Images" },
        { id: "render", msg: "Render" },
      ];

      steps.forEach(({ id, msg }) => {
        act(() => {
          result.current.setStep(id, msg);
        });
        expect(result.current.autoRunState.step).toBe(id);
        expect(result.current.autoRunState.message).toBe(msg);
      });
    });
  });

  describe("setError", () => {
    it("should set error state with default message", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setError("images", "API failed");
      });

      expect(result.current.autoRunState).toEqual({
        status: "error",
        step: "images",
        message: "Autopilot failed.",
        error: "API failed",
      });
      expect(result.current.isAutoRunning).toBe(false);
    });

    it("should set error state with cancelled message", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setError("images", "Autopilot cancelled");
      });

      expect(result.current.autoRunState).toEqual({
        status: "error",
        step: "images",
        message: "Autopilot cancelled.",
        error: "Autopilot cancelled",
      });
    });

    it("should accept idle step for error state", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setError("idle", "Initialization error");
      });

      expect(result.current.autoRunState.step).toBe("idle");
      expect(result.current.autoRunState.error).toBe("Initialization error");
    });
  });

  describe("setDone", () => {
    it("should set done state", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setDone();
      });

      expect(result.current.autoRunState).toEqual({
        status: "done",
        step: "render",
        message: "Autopilot complete.",
      });
      expect(result.current.isAutoRunning).toBe(false);
    });
  });

  describe("checkCancelled", () => {
    it("should throw error when cancelled", () => {
      const { result } = renderHook(() => useAutopilot());

      // Set step first
      act(() => {
        result.current.setStep("images", "Generating images...");
      });

      // Verify running state
      expect(result.current.isAutoRunning).toBe(true);

      // Then cancel
      act(() => {
        result.current.cancel();
      });

      // Now checkCancelled should throw
      let thrownError: Error | null = null;
      try {
        result.current.checkCancelled();
      } catch (error) {
        thrownError = error as Error;
      }

      expect(thrownError).toBeInstanceOf(Error);
      expect(thrownError?.message).toBe("Autopilot cancelled");
    });

    it("should not throw when not cancelled", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setStep("images", "Generating images...");
      });

      expect(() => {
        result.current.checkCancelled();
      }).not.toThrow();
    });
  });

  describe("cancel", () => {
    it("should set cancel flag and log when running", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setStep("images", "Generating images...");
      });

      expect(result.current.isAutoRunning).toBe(true);

      act(() => {
        result.current.cancel();
      });

      expect(result.current.autoRunLog).toContain("Autopilot cancel requested");
    });

    it("should not log when not running", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.cancel();
      });

      expect(result.current.autoRunLog).toEqual([]);
    });
  });

  describe("reset", () => {
    it("should reset all state to initial values", () => {
      const { result } = renderHook(() => useAutopilot());

      // Set some state
      act(() => {
        result.current.setStep("images", "Generating...");
        result.current.pushLog("Log 1");
        result.current.pushLog("Log 2");
        result.current.cancel();
      });

      // Reset
      act(() => {
        result.current.reset();
      });

      expect(result.current.autoRunState).toEqual({
        status: "idle",
        step: "idle",
        message: "",
      });
      expect(result.current.autoRunLog).toEqual([]);
      expect(result.current.isAutoRunning).toBe(false);
    });
  });

  describe("startRun", () => {
    it("should clear cancel flag and logs", () => {
      const { result } = renderHook(() => useAutopilot());

      // Add some logs
      act(() => {
        result.current.pushLog("Old log 1");
        result.current.pushLog("Old log 2");
      });

      act(() => {
        result.current.startRun();
      });

      expect(result.current.autoRunLog).toEqual([]);
    });
  });

  describe("getCheckpoint", () => {
    it("should return null when idle", () => {
      const { result } = renderHook(() => useAutopilot());

      const checkpoint = result.current.getCheckpoint();
      expect(checkpoint).toBeNull();
    });

    it("should create checkpoint when running", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setStep("images", "Generating images...");
      });

      const checkpoint = result.current.getCheckpoint();
      expect(checkpoint).toMatchObject({
        step: "images",
        interrupted: true,
      });
      expect(checkpoint?.timestamp).toBeGreaterThan(0);
    });

    it("should create checkpoint when done (not interrupted)", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setDone();
      });

      const checkpoint = result.current.getCheckpoint();
      expect(checkpoint).toMatchObject({
        step: "render",
        interrupted: false,
      });
    });

    it("should mark checkpoint as interrupted on error", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setError("render", "Render failed");
      });

      const checkpoint = result.current.getCheckpoint();
      expect(checkpoint).toMatchObject({
        step: "render",
        interrupted: true,
      });
    });
  });

  describe("initializeFromCheckpoint", () => {
    it("should restore interrupted checkpoint", () => {
      const { result } = renderHook(() => useAutopilot());

      const checkpoint = {
        step: "images" as const,
        timestamp: Date.now(),
        interrupted: true,
      };

      act(() => {
        result.current.initializeFromCheckpoint(checkpoint);
      });

      expect(result.current.autoRunState).toEqual({
        status: "idle",
        step: "images",
        message: "Autopilot was interrupted",
      });
    });

    it("should restore completed checkpoint", () => {
      const { result } = renderHook(() => useAutopilot());

      const checkpoint = {
        step: "render" as const,
        timestamp: Date.now(),
        interrupted: false,
      };

      act(() => {
        result.current.initializeFromCheckpoint(checkpoint);
      });

      expect(result.current.autoRunState).toEqual({
        status: "idle",
        step: "render",
        message: "Ready to resume",
      });
    });
  });

  describe("autoRunProgress", () => {
    it("should calculate progress for each step", () => {
      const { result } = renderHook(() => useAutopilot());

      // Idle = 0%
      expect(result.current.autoRunProgress).toBe(0);

      // Images = 1/2 = 50%
      act(() => {
        result.current.setStep("images", "Images");
      });
      expect(result.current.autoRunProgress).toBe(50);

      // Render = 2/2 = 100%
      act(() => {
        result.current.setStep("render", "Render");
      });
      expect(result.current.autoRunProgress).toBe(100);
    });

    it("should return 100% when done", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setDone();
      });

      expect(result.current.autoRunProgress).toBe(100);
    });

    it("should maintain progress when in error state", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.setStep("render", "Rendering...");
      });

      const progressBeforeError = result.current.autoRunProgress;

      act(() => {
        result.current.setError("render", "Failed");
      });

      expect(result.current.autoRunProgress).toBe(progressBeforeError);
    });
  });

  describe("Integration Flow", () => {
    it("should handle complete autopilot lifecycle", () => {
      const { result } = renderHook(() => useAutopilot());

      // Start
      act(() => {
        result.current.startRun();
      });
      expect(result.current.autoRunLog).toEqual([]);

      // Step 1: Images
      act(() => {
        result.current.setStep("images", "Generating images...");
        result.current.pushLog("Images started");
      });
      expect(result.current.isAutoRunning).toBe(true);
      expect(result.current.autoRunProgress).toBe(50);

      // Step 2: Render
      act(() => {
        result.current.setStep("render", "Rendering...");
        result.current.pushLog("Render started");
      });
      expect(result.current.autoRunProgress).toBe(100);

      // Done
      act(() => {
        result.current.setDone();
      });
      expect(result.current.isAutoRunning).toBe(false);
      expect(result.current.autoRunState.message).toBe("Autopilot complete.");
    });

    it("should handle cancellation during run", () => {
      const { result } = renderHook(() => useAutopilot());

      act(() => {
        result.current.startRun();
        result.current.setStep("images", "Generating images...");
      });

      act(() => {
        result.current.cancel();
      });

      expect(() => {
        result.current.checkCancelled();
      }).toThrow("Autopilot cancelled");

      act(() => {
        result.current.setError("images", "Autopilot cancelled");
      });

      expect(result.current.autoRunState.message).toBe("Autopilot cancelled.");
      expect(result.current.autoRunState.status).toBe("error");
    });

    it("should handle checkpoint save and restore", () => {
      const { result } = renderHook(() => useAutopilot());

      // Run until images step
      act(() => {
        result.current.startRun();
        result.current.setStep("images", "Generating images...");
        result.current.pushLog("Images in progress");
      });

      // Save checkpoint
      const checkpoint = result.current.getCheckpoint();
      expect(checkpoint?.step).toBe("images");
      expect(checkpoint?.interrupted).toBe(true);

      // Simulate page reload - reset state
      act(() => {
        result.current.reset();
      });
      expect(result.current.autoRunState.step).toBe("idle");

      // Restore checkpoint
      if (checkpoint) {
        act(() => {
          result.current.initializeFromCheckpoint(checkpoint);
        });
        expect(result.current.autoRunState.step).toBe("images");
        expect(result.current.autoRunState.message).toBe("Autopilot was interrupted");
      }
    });
  });
});
