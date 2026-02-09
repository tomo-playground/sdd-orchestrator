"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "../../constants";

type CharacterOption = { id: number; name: string };

type Props = {
  structure: string;
  inputClass: string;
  labelClass: string;
  onChange: (ids: Record<string, number>) => void;
};

export default function CharacterPicker({ structure, inputClass, labelClass, onChange }: Props) {
  const [characters, setCharacters] = useState<CharacterOption[]>([]);
  const [speakerA, setSpeakerA] = useState<number | null>(null);
  const [speakerB, setSpeakerB] = useState<number | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/characters`)
      .then((res) => res.json())
      .then((data) => setCharacters(data.items ?? data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const ids: Record<string, number> = {};
    if (speakerA !== null) ids["A"] = speakerA;
    if (speakerB !== null) ids["B"] = speakerB;
    onChange(ids);
  }, [speakerA, speakerB, onChange]);

  if (characters.length === 0) return null;

  const renderSelect = (
    label: string,
    value: number | null,
    setter: (v: number | null) => void
  ) => (
    <div>
      <p className="mb-0.5 text-[10px] text-zinc-400">{label}</p>
      <select
        value={value ?? ""}
        onChange={(e) => setter(e.target.value ? Number(e.target.value) : null)}
        className={inputClass}
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
    <div className="space-y-2">
      <label className={labelClass}>Characters (optional)</label>
      <div className="grid grid-cols-2 gap-3">
        {renderSelect("Speaker A", speakerA, setSpeakerA)}
        {renderSelect("Speaker B", speakerB, setSpeakerB)}
      </div>
    </div>
  );
}
