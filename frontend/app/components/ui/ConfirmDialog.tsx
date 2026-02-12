"use client";

import { useState, useCallback, useRef } from "react";
import Modal from "./Modal";
import Button from "./Button";

// ── Types ────────────────────────────────────────────────────
export type ConfirmVariant = "default" | "danger";

export type InputFieldConfig = {
  label: string;
  placeholder?: string;
  defaultValue?: string;
};

export type ConfirmDialogProps = {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  title?: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmVariant;
  inputField?: InputFieldConfig;
  inputValue?: string;
  onInputChange?: (value: string) => void;
};

// ── Component ────────────────────────────────────────────────
export default function ConfirmDialog({
  open,
  onConfirm,
  onCancel,
  title = "Confirm",
  message = "Are you sure?",
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  inputField,
  inputValue,
  onInputChange,
}: ConfirmDialogProps) {
  return (
    <Modal open={open} onClose={onCancel} size="sm" persistent>
      <Modal.Header>
        <h3 className="text-base font-semibold text-zinc-900">{title}</h3>
      </Modal.Header>

      <div className="px-5 py-4 text-sm text-zinc-600">{message}</div>

      {inputField && (
        <div className="px-5 pb-2">
          <label className="mb-1 block text-xs font-semibold text-zinc-500">
            {inputField.label}
          </label>
          <input
            type="text"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
            placeholder={inputField.placeholder}
            value={inputValue ?? ""}
            onChange={(e) => onInputChange?.(e.target.value)}
            autoFocus
          />
        </div>
      )}

      <Modal.Footer>
        <Button variant="ghost" size="sm" onClick={onCancel}>
          {cancelLabel}
        </Button>
        <Button variant={variant === "danger" ? "danger" : "primary"} size="sm" onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}

// ── useConfirm hook ──────────────────────────────────────────
type ConfirmOptions = {
  title?: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmVariant;
  inputField?: InputFieldConfig;
};

type ConfirmState = ConfirmOptions & { open: boolean };

const INITIAL_STATE: ConfirmState = { open: false };

/**
 * Promise-based confirm dialog hook. Replaces `window.confirm` and `window.prompt`.
 *
 * @example
 * const { confirm, dialogProps } = useConfirm();
 * // Boolean confirm:
 * const ok = await confirm({ title: "Delete?", variant: "danger" });
 * // Input prompt:
 * const result = await confirm({ title: "Name?", inputField: { label: "Name" } });
 * if (result !== false) { const name = result as string; }
 */
export function useConfirm() {
  const [state, setState] = useState<ConfirmState>(INITIAL_STATE);
  const [inputValue, setInputValue] = useState("");
  const resolveRef = useRef<((v: boolean | string) => void) | null>(null);
  const inputRef = useRef(inputValue);
  inputRef.current = inputValue;
  const hasInputField = !!state.inputField;

  const confirm = useCallback((opts: ConfirmOptions = {}): Promise<boolean | string> => {
    return new Promise<boolean | string>((resolve) => {
      resolveRef.current = resolve;
      setInputValue(opts.inputField?.defaultValue ?? "");
      setState({ ...opts, open: true });
    });
  }, []);

  const handleConfirm = useCallback(() => {
    resolveRef.current?.(hasInputField ? inputRef.current : true);
    resolveRef.current = null;
    setState(INITIAL_STATE);
    setInputValue("");
  }, [hasInputField]);

  const handleCancel = useCallback(() => {
    resolveRef.current?.(false);
    resolveRef.current = null;
    setState(INITIAL_STATE);
    setInputValue("");
  }, []);

  const dialogProps: ConfirmDialogProps = {
    open: state.open,
    onConfirm: handleConfirm,
    onCancel: handleCancel,
    title: state.title,
    message: state.message,
    confirmLabel: state.confirmLabel,
    cancelLabel: state.cancelLabel,
    variant: state.variant,
    inputField: state.inputField,
    inputValue,
    onInputChange: setInputValue,
  };

  return { confirm, dialogProps } as const;
}
