"use client";

import { useState, useCallback, useRef } from "react";
import Modal from "./Modal";
import Button from "./Button";

// ── Types ────────────────────────────────────────────────────
export type ConfirmVariant = "default" | "danger";

export type ConfirmDialogProps = {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  title?: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmVariant;
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
}: ConfirmDialogProps) {
  return (
    <Modal open={open} onClose={onCancel} size="sm" persistent>
      <Modal.Header>
        <h3 className="text-base font-semibold text-zinc-900">{title}</h3>
      </Modal.Header>

      <div className="px-5 py-4 text-sm text-zinc-600">{message}</div>

      <Modal.Footer>
        <Button variant="ghost" size="sm" onClick={onCancel}>
          {cancelLabel}
        </Button>
        <Button
          variant={variant === "danger" ? "danger" : "primary"}
          size="sm"
          onClick={onConfirm}
        >
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
};

type ConfirmState = ConfirmOptions & { open: boolean };

const INITIAL_STATE: ConfirmState = { open: false };

/**
 * Promise-based confirm dialog hook. Replaces `window.confirm`.
 *
 * @example
 * const { confirm, dialogProps } = useConfirm();
 * const ok = await confirm({ title: "Delete?", variant: "danger" });
 */
export function useConfirm() {
  const [state, setState] = useState<ConfirmState>(INITIAL_STATE);
  const resolveRef = useRef<((v: boolean) => void) | null>(null);

  const confirm = useCallback((opts: ConfirmOptions = {}): Promise<boolean> => {
    return new Promise<boolean>((resolve) => {
      resolveRef.current = resolve;
      setState({ ...opts, open: true });
    });
  }, []);

  const handleConfirm = useCallback(() => {
    resolveRef.current?.(true);
    resolveRef.current = null;
    setState(INITIAL_STATE);
  }, []);

  const handleCancel = useCallback(() => {
    resolveRef.current?.(false);
    resolveRef.current = null;
    setState(INITIAL_STATE);
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
  };

  return { confirm, dialogProps } as const;
}
