"""Normalize character prompts to Danbooru standard (underscores)."""

from database import SessionLocal
from models.character import Character


def normalize_tag(tag: str) -> str:
    """Normalize a single tag to Danbooru standard."""
    tag = tag.strip()
    if not tag:
        return ""

    # Handle LoRA tags
    if tag.startswith("<lora:"):
        return tag

    # Handle weighted tags or brackets: (tag), (tag:1.2), ((tag)), etc.
    # We want to replace spaces with underscores only in the actual tag part
    if "(" in tag:
        # Use a regex to find all text parts that are not weights or control characters
        # This is a bit complex, simplest is to just replace all spaces with underscores
        # EXCEPT inside <lora:...> which we already handled.
        # Danbooru tags in SB usually don't have spaces even in weights.
        return tag.replace(" ", "_")

    return tag.replace(" ", "_")


def normalize_prompt(prompt: str) -> str:
    """Normalize a full prompt string."""
    if not prompt:
        return prompt
    tags = [t.strip() for t in prompt.split(",") if t.strip()]
    normalized_tags = [normalize_tag(t) for t in tags]
    return ", ".join([t for t in normalized_tags if t])


def main():
    db = SessionLocal()
    try:
        characters = db.query(Character).all()
        print(f"Normalizing prompts for {len(characters)} characters...")

        for char in characters:
            print(f"Character: {char.name}")

            orig_base = char.custom_base_prompt
            char.custom_base_prompt = normalize_prompt(char.custom_base_prompt)
            if orig_base != char.custom_base_prompt:
                print(f"  Base: {orig_base} -> {char.custom_base_prompt}")

            orig_neg = char.custom_negative_prompt
            char.custom_negative_prompt = normalize_prompt(char.custom_negative_prompt)
            if orig_neg != char.custom_negative_prompt:
                print(f"  Neg: {orig_neg} -> {char.custom_negative_prompt}")

            orig_ref_base = char.reference_base_prompt
            char.reference_base_prompt = normalize_prompt(char.reference_base_prompt)
            if orig_ref_base != char.reference_base_prompt:
                print(f"  Ref Base: {orig_ref_base} -> {char.reference_base_prompt}")

            orig_ref_neg = char.reference_negative_prompt
            char.reference_negative_prompt = normalize_prompt(char.reference_negative_prompt)
            if orig_ref_neg != char.reference_negative_prompt:
                print(f"  Ref Neg: {orig_ref_neg} -> {char.reference_negative_prompt}")

        db.commit()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
