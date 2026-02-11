type SectionDividerProps = {
  label: string;
};

export default function SectionDivider({ label }: SectionDividerProps) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[12px] font-semibold tracking-[0.3em] text-zinc-500 uppercase">
        {label}
      </span>
      <div className="h-px flex-1 bg-zinc-200/70" />
    </div>
  );
}
