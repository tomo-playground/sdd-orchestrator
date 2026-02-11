import { create } from "zustand";
import type { Toast } from "../types";

interface UIState {
  toast: Toast;
  showToast: (message: string, type: "success" | "error" | "warning") => void;
}

export const useUIStore = create<UIState>((set) => ({
  toast: null,
  showToast: (message, type) => {
    set({ toast: { message, type } });
    setTimeout(() => set({ toast: null }), 3000);
  },
}));
