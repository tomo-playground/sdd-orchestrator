"use client";

import type { WizardTemplate } from "../wizardTemplates";
import { cx } from "../../../../components/ui/variants";

type TemplateCardProps = {
  template: WizardTemplate;
  selected: boolean;
  onSelect: (template: WizardTemplate) => void;
};

export default function TemplateCard({ template, selected, onSelect }: TemplateCardProps) {
  return (
    <button
      onClick={() => onSelect(template)}
      className={cx(
        "flex flex-col items-center gap-1.5 rounded-xl border-2 p-3 text-center transition-all hover:shadow-sm",
        selected
          ? "border-zinc-900 bg-zinc-50 shadow-sm"
          : "border-zinc-200 bg-white hover:border-zinc-300"
      )}
    >
      <span className="text-2xl">{template.emoji}</span>
      <span className="text-xs font-semibold text-zinc-800">{template.name}</span>
      <span className="text-[11px] text-zinc-400">{template.description}</span>
    </button>
  );
}
