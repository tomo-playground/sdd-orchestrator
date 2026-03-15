import { describe, it, expect, beforeEach } from "vitest";
import { useChatStore } from "../useChatStore";
import type { UserMessage } from "../../types/chat";

function makeChatMsg(id: string, text: string): UserMessage {
  return {
    id,
    role: "user",
    contentType: "user",
    text,
    timestamp: Date.now(),
  };
}

describe("useChatStore", () => {
  beforeEach(() => {
    useChatStore.setState({ histories: {} });
  });

  describe("getMessages / saveMessages with null key", () => {
    it("saves and retrieves messages with storyboardId=null using temp key", () => {
      const msgs = [makeChatMsg("1", "hello")];
      useChatStore.getState().saveMessages(null, msgs);

      const result = useChatStore.getState().getMessages(null);
      expect(result).toHaveLength(1);
      expect((result[0] as UserMessage).text).toBe("hello");
    });

    it("returns empty array when no temp messages exist", () => {
      expect(useChatStore.getState().getMessages(null)).toEqual([]);
    });
  });

  describe("getMessages / saveMessages with numeric id", () => {
    it("saves and retrieves messages with storyboardId=42", () => {
      const msgs = [makeChatMsg("1", "scene1")];
      useChatStore.getState().saveMessages(42, msgs);

      expect(useChatStore.getState().getMessages(42)).toHaveLength(1);
      expect(useChatStore.getState().getMessages(null)).toEqual([]);
    });
  });

  describe("clearMessages with null key", () => {
    it("clears temp messages when storyboardId=null", () => {
      useChatStore.getState().saveMessages(null, [makeChatMsg("1", "tmp")]);
      expect(useChatStore.getState().getMessages(null)).toHaveLength(1);

      useChatStore.getState().clearMessages(null);
      expect(useChatStore.getState().getMessages(null)).toEqual([]);
    });
  });

  describe("migrateFromTemp", () => {
    it("moves temp messages to the new storyboard id", () => {
      const msgs = [makeChatMsg("1", "topic analysis"), makeChatMsg("2", "result")];
      useChatStore.getState().saveMessages(null, msgs);

      useChatStore.getState().migrateFromTemp(100);

      // temp key should be empty
      expect(useChatStore.getState().getMessages(null)).toEqual([]);
      // new id should have the messages
      const migrated = useChatStore.getState().getMessages(100);
      expect(migrated).toHaveLength(2);
      expect((migrated[0] as UserMessage).text).toBe("topic analysis");
    });

    it("does nothing when no temp messages exist", () => {
      useChatStore.getState().saveMessages(50, [makeChatMsg("1", "existing")]);

      useChatStore.getState().migrateFromTemp(50);

      // existing messages should remain untouched
      expect(useChatStore.getState().getMessages(50)).toHaveLength(1);
      expect((useChatStore.getState().getMessages(50)[0] as UserMessage).text).toBe("existing");
    });

    it("does not affect other storyboard entries", () => {
      useChatStore.getState().saveMessages(null, [makeChatMsg("1", "temp")]);
      useChatStore.getState().saveMessages(77, [makeChatMsg("2", "other")]);

      useChatStore.getState().migrateFromTemp(200);

      expect(useChatStore.getState().getMessages(77)).toHaveLength(1);
      expect(useChatStore.getState().getMessages(200)).toHaveLength(1);
      expect(useChatStore.getState().getMessages(null)).toEqual([]);
    });
  });
});
