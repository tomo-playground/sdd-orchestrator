/**
 * Pure helper functions for tag & LoRA toggling.
 * Shared between character wizard (new) and character edit page.
 */

import type { WizardTag } from "../builder/steps/AppearanceStep";
import type { WizardCategory } from "../builder/wizardTemplates";

/** Toggle a tag considering category constraints (single-select, maxSelect). */
export function applyTagToggle(
  prev: WizardTag[],
  tag: WizardTag,
  category: WizardCategory,
): WizardTag[] {
  const exists = prev.some((t) => t.tagId === tag.tagId);
  if (exists) return prev.filter((t) => t.tagId !== tag.tagId);

  if (category.selectMode === "single") {
    return [...prev.filter((t) => t.groupName !== category.groupName), tag];
  }
  if (category.maxSelect) {
    const groupCount = prev.filter((t) => t.groupName === category.groupName).length;
    if (groupCount >= category.maxSelect) return prev;
  }
  return [...prev, tag];
}

/** Toggle a tag that has no wizard category (from search). */
export function applyFreeTagToggle(prev: WizardTag[], tag: WizardTag): WizardTag[] {
  const exists = prev.some((t) => t.tagId === tag.tagId);
  if (exists) return prev.filter((t) => t.tagId !== tag.tagId);
  return [...prev, tag];
}
