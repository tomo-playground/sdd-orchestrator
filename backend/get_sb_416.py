import json

from sqlalchemy import text

from database import engine


def get_storyboard_info(storyboard_id):
    with engine.connect() as conn:
        # Get Storyboard info
        sb_res = conn.execute(text("SELECT * FROM storyboards WHERE id = :id"), {"id": storyboard_id}).fetchone()
        if not sb_res:
            print(f"Storyboard {storyboard_id} not found.")
            return

        sb_data = dict(sb_res._mapping)
        print(f"--- Storyboard {storyboard_id} ---")
        print(json.dumps({k: str(v) for k, v in sb_data.items()}, indent=2, ensure_ascii=False))

        # Get Scenes info
        scenes_res = conn.execute(text('SELECT * FROM scenes WHERE storyboard_id = :id ORDER BY "order"'), {"id": storyboard_id}).fetchall()
        print(f"\n--- Scenes ({len(scenes_res)}) ---")
        for s in scenes_res:
            s_data = dict(s._mapping)
            # Check for image_asset_id to see if image exists
            image_asset_id = s_data.get('image_asset_id')
            image_url = None
            if image_asset_id:
                asset_res = conn.execute(text("SELECT * FROM media_assets WHERE id = :id"), {"id": image_asset_id}).fetchone()
                if asset_res:
                    image_url = asset_res._mapping.get('storage_key')

            print(f"Scene {s_data['order']}: match_rate=None, TTS=None, Image={image_url}")
            print(f"  Script: {s_data.get('script')}")
            print(f"  Caption: {s_data.get('caption')}")

            # Check for match_rate from activity_logs or scene_quality_scores
            score_res = conn.execute(text("SELECT match_rate FROM scene_quality_scores WHERE scene_id = :sid ORDER BY validated_at DESC LIMIT 1"), {"sid": s_data['id']}).fetchone()
            if score_res:
                print(f"  Match Rate (latest): {score_res[0]}")

if __name__ == "__main__":
    get_storyboard_info(416)
