"use client";

import type { AutoRunState } from "../../types";
import { AUTO_RUN_STEPS } from "../../constants";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import LoadingSpinner from "../ui/LoadingSpinner";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";

type AutoRunProgressModalProps = {
  autoRunState: AutoRunState;
  autoRunLog: string[];
  autoRunProgress: number;
  onCancel: () => void;
};

export default function AutoRunProgressModal({
  autoRunState,
  autoRunLog,
  autoRunProgress,
  onCancel,
}: AutoRunProgressModalProps) {
  const trapRef = useFocusTrap(true);
  const { confirm, dialogProps } = useConfirm();

  return (
    <div
      className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/40 px-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Autopilot Running"
    >
      <div
        ref={trapRef}
        tabIndex={-1}
        className="w-full max-w-md rounded-3xl border border-white/60 bg-white/90 p-6 text-sm text-zinc-700 shadow-2xl outline-none"
      >
        <div className="mb-3 flex items-center justify-between text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          <div className="flex items-center gap-2">
            <LoadingSpinner size="sm" color="text-zinc-500" />
            <span>Autopilot Running</span>
          </div>
          <span>
            Step {AUTO_RUN_STEPS.findIndex((step) => step.id === autoRunState.step) + 1}/
            {AUTO_RUN_STEPS.length}
          </span>
        </div>
        <div className="mb-4 h-2 w-full overflow-hidden rounded-full bg-zinc-200">
          <div
            className="h-full rounded-full bg-zinc-900 transition-all duration-500"
            style={{ width: `${autoRunProgress}%` }}
          />
        </div>
        <p className="text-base font-semibold text-zinc-900">{autoRunState.message}</p>
        {autoRunLog.length > 0 && (
          <div className="mt-3 grid max-h-32 gap-1 overflow-y-auto rounded-xl border border-zinc-100 bg-zinc-50 p-3 text-[13px] text-zinc-500">
            {autoRunLog.map((entry, idx) => (
              <span key={`${entry}-${idx}`}>• {entry}</span>
            ))}
          </div>
        )}
        <button
          type="button"
          onClick={async () => {
            const ok = await confirm({
              title: "Cancel Autopilot",
              message: "Autopilot을 취소하시겠습니까?",
              confirmLabel: "Cancel",
              variant: "danger",
            });
            if (ok) onCancel();
          }}
          className="mt-5 w-full rounded-full border border-zinc-300 bg-white px-4 py-2 text-[12px] font-semibold tracking-[0.2em] text-zinc-700 uppercase hover:border-zinc-400 hover:bg-zinc-50"
        >
          Cancel Autopilot
        </button>
        <ConfirmDialog {...dialogProps} />
      </div>
    </div>
  );
}
