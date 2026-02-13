"use client";

import type { ActorGender } from "../../../../types";
import type { WizardTemplate } from "../wizardTemplates";
import TemplateCard from "../components/TemplateCard";
import { WIZARD_TEMPLATES } from "../wizardTemplates";
import {
  FORM_INPUT_CLASSES,
  FORM_LABEL_CLASSES,
  FORM_TEXTAREA_CLASSES,
} from "../../../../components/ui/variants";

type BasicInfoStepProps = {
  name: string;
  gender: ActorGender;
  description: string;
  templateId: string | null;
  onNameChange: (v: string) => void;
  onGenderChange: (v: ActorGender) => void;
  onDescriptionChange: (v: string) => void;
  onTemplateSelect: (t: WizardTemplate) => void;
};

export default function BasicInfoStep({
  name,
  gender,
  description,
  templateId,
  onNameChange,
  onGenderChange,
  onDescriptionChange,
  onTemplateSelect,
}: BasicInfoStepProps) {
  return (
    <div className="space-y-6">
      {/* Quick Start Templates */}
      <section>
        <h3 className={`${FORM_LABEL_CLASSES} mb-3`}>Quick Start</h3>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
          {WIZARD_TEMPLATES.map((t) => (
            <TemplateCard
              key={t.id}
              template={t}
              selected={templateId === t.id}
              onSelect={onTemplateSelect}
            />
          ))}
        </div>
      </section>

      {/* Name */}
      <section>
        <label className={`${FORM_LABEL_CLASSES} mb-1 block`}>Name *</label>
        <input
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="Character name (2+ characters)"
          className={FORM_INPUT_CLASSES}
          maxLength={50}
          autoFocus
        />
      </section>

      {/* Gender */}
      <section>
        <label className={`${FORM_LABEL_CLASSES} mb-2 block`}>Gender</label>
        <div className="flex gap-2">
          {(["female", "male"] as const).map((g) => (
            <button
              key={g}
              onClick={() => onGenderChange(g)}
              className={`rounded-full px-4 py-1.5 text-xs font-medium transition ${
                gender === g
                  ? "bg-zinc-900 text-white"
                  : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200"
              }`}
            >
              {g === "female" ? "Female" : "Male"}
            </button>
          ))}
        </div>
      </section>

      {/* Description */}
      <section>
        <label className={`${FORM_LABEL_CLASSES} mb-1 block`}>Description</label>
        <textarea
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="Brief character description (optional)"
          className={FORM_TEXTAREA_CLASSES}
          rows={3}
          maxLength={500}
        />
      </section>
    </div>
  );
}
