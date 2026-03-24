/** Structure가 다중 캐릭터(dialogue/narrated_dialogue)인지 판정 */
export function isMultiCharStructure(structure: string): boolean {
  return structure === "dialogue" || structure === "narrated_dialogue";
}
