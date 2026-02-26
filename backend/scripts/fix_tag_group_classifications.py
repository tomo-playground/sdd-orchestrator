"""Fix tag group_name misclassifications discovered in storyboard 481 analysis.

Fixes:
1. confused: subject → expression
2. clothing → footwear (60 tags)
3. clothing → legwear (74 tags)
4. clothing → accessory (~200 tags, excluding false positives)
5. clothing false positives → correct groups (subject, clothing_bottom)
6. location_indoor misclassifications (~22 tags)
7. environment misclassifications (~45 tags)

After running this, run fix_tag_default_layers.py to sync default_layer values.

Usage:
    python scripts/fix_tag_group_classifications.py --dry-run
    python scripts/fix_tag_group_classifications.py
"""

import argparse

from config import logger
from database import SessionLocal
from models import Tag

# ── Reclassification rules ────────────────────────────────────────────

RULES: list[dict] = [
    # 1. confused: subject → expression
    {
        "desc": "confused → expression",
        "filter": lambda t: t.name == "confused" and t.group_name == "subject",
        "new_group": "expression",
    },
    # 2. clothing → footwear
    {
        "desc": "clothing → footwear",
        "filter": lambda t: (
            t.group_name == "clothing"
            and any(
                p in t.name
                for p in (
                    "boots", "shoes", "sneakers", "sandals", "slippers",
                    "footwear", "loafers", "heels", "pumps",
                )
            )
            or t.name in ("mary_janes",)
        ),
        "new_group": "footwear",
    },
    # 3. clothing → legwear (exclude footwear overlap)
    {
        "desc": "clothing → legwear",
        "filter": lambda t: (
            t.group_name == "clothing"
            and any(
                p in t.name
                for p in (
                    "stockings", "socks", "thighhighs", "pantyhose",
                    "leggings", "kneehighs", "legwear", "tights",
                )
            )
            # garter는 legwear에 포함 (garter_belt, garter_straps 등)
            or (t.group_name == "clothing" and "garter" in t.name
                and "belt" not in t.name.replace("garter_belt", ""))
        ),
        "new_group": "legwear",
    },
    # 4. clothing → accessory (hat/glasses/jewelry/scarf/belt 등)
    {
        "desc": "clothing → accessory",
        "filter": lambda t: (
            t.group_name == "clothing"
            and any(
                p in t.name
                for p in (
                    "hat", "glasses", "sunglasses", "goggles", "earring",
                    "necklace", "bracelet", "choker", "scarf", "beret",
                    "crown", "tiara", "brooch", "pendant", "headphones",
                    "earmuffs", "backpack", "purse",
                )
            )
            # 아래는 제외 (false positive)
            and t.name not in (
                "baggy_pants", "capri_pants", "string_bikini", "o-ring_bikini",
                "load_bearing_vest", "chi-hatan_military_uniform",
            )
        ),
        "new_group": "accessory",
    },
    # 4-b. clothing bag/belt/ring/cap/mask → accessory (좁은 패턴)
    {
        "desc": "clothing bag/belt/ring/cap/mask → accessory",
        "filter": lambda t: (
            t.group_name == "clothing"
            and (
                (t.name.endswith("_bag") and t.name not in (
                    "bag_of_chips", "blood_bag", "paper_bag",
                    "pastry_bag", "plastic_bag", "trash_bag",
                ))
                or t.name in ("bag", "bag_charm")
                or (("belt" in t.name or t.name.endswith("_belt"))
                    and t.name not in ("belt_boots",))
                or (t.name.endswith("_ring") and t.name not in ("wrestling_ring",))
                or t.name in ("ring",)
                or t.name in (
                    "cap", "baseball_cap", "garrison_cap", "jester_cap",
                    "mob_cap", "nurse_cap", "peaked_cap", "shako_cap",
                    "swim_cap", "visor_cap", "flat_cap",
                )
                or t.name in ("pocket_watch", "wedding_ring")
            )
        ),
        "new_group": "accessory",
    },
    # 4-c. clothing false positives → subject
    {
        "desc": "clothing non-clothing → subject",
        "filter": lambda t: (
            t.group_name == "clothing"
            and t.name in (
                "bag_of_chips", "bean_bag_chair", "blood_bag", "paper_bag",
                "pastry_bag", "plastic_bag", "trash_bag", "wrestling_ring",
            )
        ),
        "new_group": "subject",
    },
    # 4-d. hat_tip → gesture, oguri_cap → subject
    {
        "desc": "clothing misc → correct groups",
        "filter": lambda t: t.group_name == "clothing" and t.name == "hat_tip",
        "new_group": "gesture",
    },
    {
        "desc": "oguri_cap → subject",
        "filter": lambda t: t.group_name == "clothing" and t.name == "oguri_cap_(umamusume)",
        "new_group": "subject",
    },
    # 4-e. single_hair_ring → hair_accessory
    {
        "desc": "single_hair_ring → hair_accessory",
        "filter": lambda t: t.group_name == "clothing" and t.name == "single_hair_ring",
        "new_group": "hair_accessory",
    },
    # 4-f. pants → clothing_bottom
    {
        "desc": "pants → clothing_bottom",
        "filter": lambda t: (
            t.group_name == "clothing"
            and t.name in ("baggy_pants", "capri_pants")
        ),
        "new_group": "clothing_bottom",
    },
    # 5. location_indoor misclassifications
    {
        "desc": "location_indoor → clothing",
        "filter": lambda t: t.group_name == "location_indoor" and t.name == "hospital_gown",
        "new_group": "clothing",
    },
    {
        "desc": "location_indoor → subject",
        "filter": lambda t: (
            t.group_name == "location_indoor"
            and t.name in (
                "office_lady", "kitchen_knife", "paper_airplane",
                "chocolate_bar", "health_bar", "nipple_bar", "spreader_bar",
                "watermelon_bar", "pool_of_blood", "cum_pool",
                "rei_no_pool", "manhattan_cafe_(umamusume)", "hakurei_shrine",
                "loaded_interior",
            )
        ),
        "new_group": "subject",
    },
    {
        "desc": "location_indoor → skip",
        "filter": lambda t: t.group_name == "location_indoor" and t.name == "bar_censor",
        "new_group": "skip",
    },
    {
        "desc": "location_indoor → location_outdoor",
        "filter": lambda t: t.group_name == "location_indoor" and t.name == "bus_stop",
        "new_group": "location_outdoor",
    },
    {
        "desc": "location_indoor → environment (furniture)",
        "filter": lambda t: (
            t.group_name == "location_indoor"
            and t.name in ("hospital_bed", "office_chair", "bar_stool",
                           "pool_ladder", "wading_pool")
        ),
        "new_group": "environment",
    },
    # 6. environment misclassifications
    {
        "desc": "environment → pose",
        "filter": lambda t: (
            t.group_name == "environment"
            and t.name in (
                "against_glass", "against_wall", "elbows_on_table",
                "head_on_pillow", "on_bed", "on_chair", "on_couch",
                "on_desk", "on_floor", "on_table", "breasts_on_glass",
                "breasts_on_table", "flower_over_eye",
                "lap_pillow", "lap_pillow_invitation",
            )
        ),
        "new_group": "pose",
    },
    {
        "desc": "environment → action",
        "filter": lambda t: (
            t.group_name == "environment"
            and t.name in (
                "curtain_grab", "pillow_grab", "pillow_hug",
                "talking_on_phone", "watching_television", "through_wall",
            )
        ),
        "new_group": "action",
    },
    {
        "desc": "environment → gaze",
        "filter": lambda t: t.group_name == "environment" and t.name == "looking_at_mirror",
        "new_group": "gaze",
    },
    {
        "desc": "environment → hair_style",
        "filter": lambda t: t.group_name == "environment" and t.name == "bowl_cut",
        "new_group": "hair_style",
    },
    {
        "desc": "environment → clothing",
        "filter": lambda t: (
            t.group_name == "environment"
            and t.name in ("breast_curtain", "pelvic_curtain", "plate_armor", "crotch_plate")
        ),
        "new_group": "clothing",
    },
    {
        "desc": "environment → accessory",
        "filter": lambda t: (
            t.group_name == "environment"
            and t.name in ("flower_ornament", "flower_knot")
        ),
        "new_group": "accessory",
    },
    {
        "desc": "environment → subject",
        "filter": lambda t: (
            t.group_name == "environment"
            and t.name in (
                "blood_on_knife", "food_in_mouth", "food_on_body",
                "food_on_face", "food_on_head", "in_cup", "in_food",
                "plant_girl", "food_art", "food_focus", "food_print",
            )
        ),
        "new_group": "subject",
    },
    {
        "desc": "environment → skip (meta)",
        "filter": lambda t: (
            t.group_name == "environment"
            and t.name in ("split_screen", "fourth_wall", "wall_of_text", "text")
        ),
        "new_group": "skip",
    },
    {
        "desc": "environment → location_outdoor",
        "filter": lambda t: t.group_name == "environment" and t.name == "traffic_jam",
        "new_group": "location_outdoor",
    },
]


def fix_tag_group_classifications(dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        tags = db.query(Tag).filter(Tag.group_name.isnot(None)).all()
        total_fixed = 0

        for rule in RULES:
            fixed = 0
            for tag in tags:
                if rule["filter"](tag):
                    logger.info(
                        "[%s] %s: group_name '%s' → '%s'",
                        "DRY-RUN" if dry_run else "FIX",
                        tag.name,
                        tag.group_name,
                        rule["new_group"],
                    )
                    if not dry_run:
                        tag.group_name = rule["new_group"]
                    fixed += 1
            if fixed > 0:
                logger.info("  Rule '%s': %d tags", rule["desc"], fixed)
                total_fixed += fixed

        if not dry_run:
            db.commit()

        logger.info(
            "Done (%s): %d total tags reclassified",
            "dry-run" if dry_run else "applied",
            total_fixed,
        )
    except Exception as e:
        logger.error("Failed: %s", e)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix tag group_name misclassifications")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    args = parser.parse_args()
    fix_tag_group_classifications(dry_run=args.dry_run)
