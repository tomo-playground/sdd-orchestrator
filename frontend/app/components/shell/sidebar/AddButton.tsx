import { Plus } from "lucide-react";

type Props = {
  label: string;
  collapsed: boolean;
  onClick: () => void;
};

export default function AddButton({ label, collapsed, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      title={collapsed ? label : undefined}
      className="mx-1 flex w-[calc(100%-0.5rem)] items-center gap-1.5 rounded-lg px-2 py-1 text-[11px] text-zinc-400 transition hover:bg-zinc-50 hover:text-zinc-600"
    >
      <Plus className="h-3 w-3 shrink-0" />
      {!collapsed && label}
    </button>
  );
}
