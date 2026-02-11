"use client";

import { useCharacters } from "../../hooks/useCharacters";
import { cx, SECTION_CLASSES, FORM_INPUT_CLASSES, FORM_LABEL_CLASSES } from "../ui/variants";

type Props = {
  structure: string;
  characterId: number | null;
  characterBId: number | null;
  onChangeA: (id: number | null) => void;
  onChangeB: (id: number | null) => void;
};

const LABEL = `mb-1 block ${FORM_LABEL_CLASSES}`;

export default function CharacterSelectSection({
  structure,
  characterId,
  characterBId,
  onChangeA,
  onChangeB,
}: Props) {
  const { characters } = useCharacters();
  const isMultiChar = structure === "Dialogue" || structure === "Narrated Dialogue";

  if (characters.length === 0) return null;

  const renderSelect = (
    label: string,
    value: number | null,
    onChange: (id: number | null) => void
  ) => (
    <div>
      <label className={LABEL}>{label}</label>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        className={FORM_INPUT_CLASSES}
      >
        <option value="">None</option>
        {characters.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <section className={cx(SECTION_CLASSES, "space-y-3")}>
      <h3 className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">Characters</h3>
      <div className={isMultiChar ? "grid grid-cols-2 gap-3" : ""}>
        {renderSelect(isMultiChar ? "Character A" : "Character", characterId, onChangeA)}
        {isMultiChar && renderSelect("Character B", characterBId, onChangeB)}
      </div>
    </section>
  );
}
