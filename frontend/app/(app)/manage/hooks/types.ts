// ── Shared UI Callback Types ──────────────────────────

export type UiCallbacks = {
  showToast: (message: string, type: "success" | "error" | "warning") => void;
  confirmDialog: (opts: {
    title?: string;
    message?: string;
    confirmLabel?: string;
    variant?: "default" | "danger";
  }) => Promise<boolean>;
};

export type UiCallbacksWithPrompt = UiCallbacks & {
  promptDialog: (msg: string) => string | null;
};
