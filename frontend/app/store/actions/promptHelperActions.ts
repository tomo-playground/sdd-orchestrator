import axios from "axios";
import { useUIStore } from "../useUIStore";
import { API_BASE } from "../../constants";

export async function suggestPromptSplit() {
  const { examplePrompt, set, showToast } = useUIStore.getState();
  if (!examplePrompt.trim()) return;

  set({ isSuggesting: true, copyStatus: "" });
  try {
    const res = await axios.post(`${API_BASE}/prompt/split`, {
      prompt: examplePrompt,
    });
    if (res.data.base || res.data.scene) {
      set({
        suggestedBase: res.data.base || "",
        suggestedScene: res.data.scene || "",
      });
    }
  } catch (error) {
    console.error("Failed to suggest prompt split:", error);
    showToast("Failed to split prompt", "error");
  } finally {
    set({ isSuggesting: false });
  }
}

export function copyPromptHelperText(text: string) {
  const { set, showToast } = useUIStore.getState();
  if (!text) return;

  navigator.clipboard
    .writeText(text)
    .then(() => {
      set({ copyStatus: "Copied to clipboard!" });
      setTimeout(() => set({ copyStatus: "" }), 2000);
    })
    .catch(() => showToast("클립보드 복사 실패", "error"));
}
