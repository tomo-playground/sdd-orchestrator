// ── Shared UI Callback Types ──────────────────────────

export type UiCallbacks = {
  showToast: (message: string, type: "success" | "error" | "warning") => void;
  confirmDialog: (opts: {
    title?: string;
    message?: string;
    confirmLabel?: string;
    variant?: "default" | "danger";
  }) => Promise<boolean | string>;
};

export type UiCallbacksWithPrompt = UiCallbacks & {
  promptDialog: (opts: {
    title: string;
    message?: string;
    inputField: { label: string; placeholder?: string; defaultValue?: string };
  }) => Promise<boolean | string>;
};
