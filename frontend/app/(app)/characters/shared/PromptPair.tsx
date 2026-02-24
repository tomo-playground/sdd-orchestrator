import TagAutocomplete from "../../../components/ui/TagAutocomplete";

type PromptPairProps = {
  label?: string;
  positiveValue: string;
  negativeValue: string;
  onPositiveChange: (value: string) => void;
  onNegativeChange: (value: string) => void;
  positivePlaceholder: string;
  negativePlaceholder: string;
};

const PROMPT_CLASSES =
  "w-full rounded-2xl border border-zinc-200 bg-white/80 p-4 text-sm shadow-inner outline-none focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200/50 disabled:cursor-not-allowed disabled:opacity-60";

export default function PromptPair({
  label,
  positiveValue,
  negativeValue,
  onPositiveChange,
  onNegativeChange,
  positivePlaceholder,
  negativePlaceholder,
}: PromptPairProps) {
  return (
    <div className="space-y-3">
      {label && <p className="text-[11px] font-medium text-zinc-400">{label}</p>}
      <div>
        <label className="mb-1 block text-xs font-medium text-zinc-500">Positive Prompt</label>
        <TagAutocomplete
          value={positiveValue}
          onChange={onPositiveChange}
          placeholder={positivePlaceholder}
          rows={3}
          className={PROMPT_CLASSES}
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-zinc-500">Negative Prompt</label>
        <TagAutocomplete
          value={negativeValue}
          onChange={onNegativeChange}
          placeholder={negativePlaceholder}
          rows={3}
          className={PROMPT_CLASSES}
        />
      </div>
    </div>
  );
}
