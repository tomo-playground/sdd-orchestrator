import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { ChatMessage } from "../types/chat";

/** 스토리보드 ID별 채팅 히스토리 영속 저장소 */

const MAX_MESSAGES_PER_STORYBOARD = 50;
const MAX_STORYBOARD_ENTRIES = 10;
const STORE_KEY = "shorts-producer:chat:v1";

/** 새 영상(storyboardId=null) 채팅을 임시 저장하는 key */
const TEMP_NEW_KEY = "__new__";

type ChatHistoryMap = Record<string, ChatMessage[]>;

export interface ChatStoreState {
  histories: ChatHistoryMap;

  /** 특정 스토리보드의 채팅 히스토리 조회 (null이면 임시 key 사용) */
  getMessages: (storyboardId: number | null) => ChatMessage[];
  /** 채팅 히스토리 저장 (null이면 임시 key에 저장) */
  saveMessages: (storyboardId: number | null, messages: ChatMessage[]) => void;
  /** 특정 스토리보드의 채팅 히스토리 삭제 */
  clearMessages: (storyboardId: number | null) => void;
  /** 임시 key → 실제 storyboardId로 채팅 히스토리 이관 */
  migrateFromTemp: (newStoryboardId: number) => void;
}

export const useChatStore = create<ChatStoreState>()(
  persist(
    (set, get) => ({
      histories: {},

      getMessages: (storyboardId) => {
        const key = storyboardId ? String(storyboardId) : TEMP_NEW_KEY;
        return get().histories[key] ?? [];
      },

      saveMessages: (storyboardId, messages) => {
        const key = storyboardId ? String(storyboardId) : TEMP_NEW_KEY;
        // pipeline_step 메시지의 nodeResult(대량 JSON)를 제거하여 5MB 제한 방지
        const sanitized: ChatMessage[] = messages.map((m) => {
          if (m.contentType === "pipeline_step") {
            return { ...m, nodeResult: {} } as ChatMessage;
          }
          return m;
        });
        const trimmed = sanitized.slice(-MAX_MESSAGES_PER_STORYBOARD);

        set((state) => {
          const next = { ...state.histories, [key]: trimmed };

          // 오래된 항목 정리 (초과 시에만 정렬 실행)
          const keys = Object.keys(next);
          if (keys.length > MAX_STORYBOARD_ENTRIES) {
            const oldest = keys
              .filter((k) => k !== key)
              .sort((a, b) => {
                const aLast = next[a]?.[next[a].length - 1]?.timestamp ?? 0;
                const bLast = next[b]?.[next[b].length - 1]?.timestamp ?? 0;
                return aLast - bLast;
              });
            for (const old of oldest.slice(0, keys.length - MAX_STORYBOARD_ENTRIES)) {
              delete next[old];
            }
          }

          return { histories: next };
        });
      },

      clearMessages: (storyboardId) => {
        const key = storyboardId ? String(storyboardId) : TEMP_NEW_KEY;
        set((state) => {
          const next = { ...state.histories };
          delete next[key];
          return { histories: next };
        });
      },

      migrateFromTemp: (newStoryboardId) => {
        set((state) => {
          const temp = state.histories[TEMP_NEW_KEY];
          if (!temp || temp.length === 0) return state;
          const next = { ...state.histories };
          next[String(newStoryboardId)] = temp;
          delete next[TEMP_NEW_KEY];
          return { histories: next };
        });
      },
    }),
    {
      name: STORE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ histories: state.histories }),
    }
  )
);
