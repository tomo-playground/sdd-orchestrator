import Textarea from "../../../components/ui/Textarea";

type PromptPairProps = {
  label?: string;
  positiveValue: string;
  negativeValue: string;
  onPositiveChange: (value: string) => void;
  onNegativeChange: (value: string) => void;
  positivePlaceholder: string;
  negativePlaceholder: string;
};

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
        <Textarea
          value={positiveValue}
          onChange={(e) => onPositiveChange(e.target.value)}
          placeholder={positivePlaceholder}
          rows={3}
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-zinc-500">Negative Prompt</label>
        <Textarea
          value={negativeValue}
          onChange={(e) => onNegativeChange(e.target.value)}
          placeholder={negativePlaceholder}
          rows={3}
        />
      </div>
    </div>
  );
}
