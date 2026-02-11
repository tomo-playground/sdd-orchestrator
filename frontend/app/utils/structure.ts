/** Structure가 다중 캐릭터(Dialogue/Narrated Dialogue)인지 판정 */
export function isMultiCharStructure(structure: string): boolean {
  return structure === "Dialogue" || structure === "Narrated Dialogue";
}
