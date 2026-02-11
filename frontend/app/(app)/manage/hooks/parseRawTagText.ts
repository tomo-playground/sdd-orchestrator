import type { Tag } from "../../../types";

/** Parse comma-separated tag text into tag IDs with case-insensitive matching. */
export function parseRawTagText(
  text: string,
  allTags: Tag[]
): { ids: number[]; notFound: string[] } {
  const parsed = text
    .split(",")
    .map((t) => t.trim())
    .filter((t) => t.length > 0);
  const ids: number[] = [];
  const notFound: string[] = [];

  parsed.forEach((tagName) => {
    let tag = allTags.find((t) => t.name === tagName);
    if (!tag) tag = allTags.find((t) => t.name.toLowerCase() === tagName.toLowerCase());
    if (tag) {
      if (!ids.includes(tag.id)) ids.push(tag.id);
    } else {
      notFound.push(tagName);
    }
  });

  return { ids, notFound };
}
