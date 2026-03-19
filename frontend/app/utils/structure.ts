/** Structure가 다중 캐릭터(dialogue/narrated_dialogue)인지 판정 */
export function isMultiCharStructure(structure: string): boolean {
  const s = structure.toLowerCase().replace(/ /g, "_");
  return s === "dialogue" || s === "narrated_dialogue";
}
