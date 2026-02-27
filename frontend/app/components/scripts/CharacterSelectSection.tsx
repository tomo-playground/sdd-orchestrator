"use client";

import { useCharacters } from "../../hooks/useCharacters";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { isMultiCharStructure } from "../../utils/structure";
import {
  cx,
  SECTION_CLASSES,
  SECTION_HEADER_CLASSES,
  FORM_INPUT_CLASSES,
  FORM_LABEL_CLASSES,
} from "../ui/variants";

type Props = {
  structure: string;
  characterId: number | null;
  characterBId: number | null;
  onChangeA: (id: number | null, name: string | null) => void;
  onChangeB: (id: number | null, name: string | null) => void;
  /** When true, render content only without the SECTION_CLASSES card wrapper. */
  embedded?: boolean;
};

const LABEL = `mb-1 block ${FORM_LABEL_CLASSES}`;

export default function CharacterSelectSection({
  structure,
  characterId,
  characterBId,
  onChangeA,
  onChangeB,
  embedded = false,
}: Props) {
  const { characters } = useCharacters();
  const casting = useStoryboardStore((s) => s.castingRecommendation);
  const isMultiChar = isMultiCharStructure(structure);

  if (characters.length === 0) return null;

  const recIds = new Set(
    [casting?.character_id, casting?.character_b_id].filter((id): id is number => id != null)
  );

  const renderSelect = (
    label: string,
    value: number | null,
    onChange: (id: number | null, name: string | null) => void
  ) => (
    <div>
      {label && <label className={LABEL}>{label}</label>}
      <select
        value={value ?? ""}
        onChange={(e) => {
          const id = e.target.value ? Number(e.target.value) : null;
          const name = id ? (characters.find((c) => c.id === id)?.name ?? null) : null;
          onChange(id, name);
        }}
        className={FORM_INPUT_CLASSES}
      >
        <option value="">None</option>
        {characters.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
            {recIds.has(c.id) ? " (AI 추천)" : ""}
          </option>
        ))}
      </select>
    </div>
  );

  const content = (
    <>
      <h3 className={SECTION_HEADER_CLASSES}>Characters</h3>
      <div className={isMultiChar ? "grid grid-cols-2 gap-3" : ""}>
        {renderSelect(isMultiChar ? "Character A" : "", characterId, onChangeA)}
        {isMultiChar && renderSelect("Character B", characterBId, onChangeB)}
      </div>
    </>
  );

  if (embedded) return <div className="space-y-3">{content}</div>;

  return <section className={cx(SECTION_CLASSES, "space-y-3")}>{content}</section>;
}
