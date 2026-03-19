import json
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL)


def get_or_create_tag(conn, tag_name):
    res = conn.execute(text("SELECT id FROM tags WHERE name = :name"), {"name": tag_name}).fetchone()
    if res:
        return res[0]

    # Insert new tag with required non-nullable columns
    res = conn.execute(
        text("""
        INSERT INTO tags (name, is_active, default_layer, priority, wd14_count, wd14_category, usage_scope) 
        VALUES (:name, true, 0, 100, 0, 0, 'ANY') 
        RETURNING id
    """),
        {"name": tag_name},
    ).fetchone()
    return res[0]


def polish_sb_416():
    storyboard_id = 416
    with engine.connect() as conn:
        print(f"Polishing Storyboard {storyboard_id}...")

        # 1. Update Scene Durations (Pacing)
        conn.execute(
            text("""
            UPDATE scenes SET duration = 3.0 WHERE storyboard_id = :id AND "order" = 4;
        """),
            {"id": storyboard_id},
        )
        conn.execute(
            text("""
            UPDATE scenes SET duration = 3.8 WHERE storyboard_id = :id AND "order" = 11;
        """),
            {"id": storyboard_id},
        )
        print("Updated durations for scenes 4 and 11.")

        # 2. Add Scene Tags and Character Actions
        scenes = conn.execute(
            text('SELECT id, "order", script FROM scenes WHERE storyboard_id = :id ORDER BY "order"'),
            {"id": storyboard_id},
        ).fetchall()

        # Clear existing to avoid duplicates during demo
        for s in scenes:
            conn.execute(text("DELETE FROM scene_tags WHERE scene_id = :sid"), {"sid": s[0]})
            conn.execute(text("DELETE FROM scene_character_actions WHERE scene_id = :sid"), {"sid": s[0]})

        for s in scenes:
            sid = s[0]
            order = s[1]

            tags = []
            char_tags = []  # For scene_character_actions

            if order == 0:  # Spring
                tags = ["cherry blossoms", "pollen flying"]
                char_tags = ["sneezing", "rubbing eyes", "annoyed face"]
            elif order == 1:  # Summer
                tags = ["scorching sun", "heat waves"]
                char_tags = ["sweating", "fanning self", "angry face"]
            elif order == 2:  # Fall
                tags = ["falling leaves", "cloudy sky"]
                char_tags = ["sighing", "lonely expression"]
            elif order == 3:  # Winter
                tags = ["heavy blizzard", "snow piles"]
                char_tags = ["shivering", "miserable expression"]
            elif order == 4:  # Enough!
                tags = ["extreme close-up"]
                char_tags = ["shouting", "furious"]
            elif order >= 6:  # Indoor Paradise
                tags = ["modern living room", "air conditioner", "warm lighting"]
                char_tags = ["relaxing on sofa", "happy smile", "blissful"]

            # Insert scene tags and update context_tags for TTS
            context_data = {
                "visual_tags": tags,
                "character_actions": char_tags,
                "mood": char_tags[0] if char_tags else "neutral",
            }

            conn.execute(
                text("UPDATE scenes SET context_tags = :ctx WHERE id = :sid"),
                {"ctx": json.dumps(context_data), "sid": sid},
            )

            for t_name in tags:
                tid = get_or_create_tag(conn, t_name)
                conn.execute(
                    text("INSERT INTO scene_tags (scene_id, tag_id, weight) VALUES (:sid, :tid, 1.0)"),
                    {"sid": sid, "tid": tid},
                )

            # Insert character actions (represented as tags in this schema)
            for t_name in char_tags:
                tid = get_or_create_tag(conn, t_name)
                conn.execute(
                    text(
                        "INSERT INTO scene_character_actions (scene_id, character_id, tag_id, weight) VALUES (:sid, 9, :tid, 1.0)"
                    ),
                    {"sid": sid, "tid": tid},
                )

            print(f"  Scene {order}: Refined with {len(tags) + len(char_tags)} tags.")

        conn.commit()
    print("Polishing data update complete.")


if __name__ == "__main__":
    polish_sb_416()
