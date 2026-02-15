"use client";

import { Brain, Trash2 } from "lucide-react";
import { useMemoryTab } from "../hooks/useMemoryTab";
import Button from "../../../components/ui/Button";
import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";

const NS_LABELS: Record<string, string> = {
  character: "Character",
  topic: "Topic",
  user: "User",
  group: "Group",
  feedback: "Feedback",
};

export default function MemoryTab() {
  const { stats, items, activeNs, setActiveNs, loading, deleteItem, deleteNamespace } =
    useMemoryTab();
  const { confirm, dialogProps } = useConfirm();

  const handleDeleteAll = async () => {
    const ok = await confirm({
      title: "전체 초기화",
      message: `${NS_LABELS[activeNs] ?? activeNs} 메모리를 모두 삭제합니다. 이 작업은 되돌릴 수 없습니다.`,
      confirmLabel: "전체 삭제",
      variant: "danger",
    });
    if (!ok) return;
    const nsIds = new Set(items.map((i) => i.namespace[1]).filter(Boolean));
    for (const nsId of nsIds) {
      await deleteNamespace(activeNs, nsId);
    }
  };

  return (
    <section className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Brain className="h-5 w-5 text-zinc-500" />
        <h2 className="text-lg font-semibold text-zinc-900">AI Memory</h2>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
          {Object.entries(NS_LABELS).map(([key, label]) => (
            <div key={key} className="rounded-lg border border-zinc-200 bg-white p-3 text-center">
              <p className="text-xs text-zinc-500">{label}</p>
              <p className="mt-1 text-xl font-semibold text-zinc-900">
                {stats.by_namespace[key] ?? 0}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Filter chips */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(NS_LABELS).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveNs(key)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              activeNs === key
                ? "bg-zinc-900 text-white"
                : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
            }`}
          >
            {label}
            {stats && ` (${stats.by_namespace[key] ?? 0})`}
          </button>
        ))}
      </div>

      {/* Items list */}
      {loading ? (
        <div className="flex justify-center py-8">
          <LoadingSpinner size="md" />
        </div>
      ) : items.length === 0 ? (
        <p className="py-8 text-center text-sm text-zinc-400">항목이 없습니다</p>
      ) : (
        <div className="flex flex-col gap-2">
          {items.map((item) => (
            <div
              key={item.key}
              className="flex items-start justify-between rounded-lg border border-zinc-200 bg-white p-3"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-mono text-xs text-zinc-400">
                  {item.namespace.join("/")}
                </p>
                <pre className="mt-1 max-h-20 overflow-auto text-xs text-zinc-700">
                  {JSON.stringify(item.value, null, 2).slice(0, 300)}
                </pre>
              </div>
              <button
                type="button"
                onClick={() => {
                  const nsId = item.namespace[1] ?? "";
                  void deleteItem(activeNs, nsId, item.key);
                }}
                className="ml-2 flex-shrink-0 rounded p-1 text-zinc-400 hover:bg-red-50 hover:text-red-500"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Delete all button */}
      {items.length > 0 && (
        <div className="flex justify-end">
          <Button size="sm" variant="danger" onClick={handleDeleteAll}>
            <Trash2 className="h-3.5 w-3.5" />
            전체 초기화
          </Button>
        </div>
      )}

      <ConfirmDialog {...dialogProps} />
    </section>
  );
}
