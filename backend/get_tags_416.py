from sqlalchemy import text
from database import engine

def get_scene_tags(storyboard_id):
    with engine.connect() as conn:
        scenes = conn.execute(text('SELECT id, "order", script FROM scenes WHERE storyboard_id = :id ORDER BY "order"'), {"id": storyboard_id}).fetchall()
        for s in scenes:
            print(f"\n--- Scene {s.order} ({s.id}) ---")
            print(f"Script: {s.script}")
            
            # Tags from scene_tags
            tags = conn.execute(text("""
                SELECT t.name, st.weight 
                FROM scene_tags st 
                JOIN tags t ON st.tag_id = t.id 
                WHERE st.scene_id = :sid
            """), {"sid": s.id}).fetchall()
            print(f"  Scene Tags: {', '.join([f'{t.name}({t.weight})' for t in tags])}")

            # Character actions
            actions = conn.execute(text("""
                SELECT t.name, sca.weight, c.name as char_name
                FROM scene_character_actions sca
                JOIN tags t ON sca.tag_id = t.id
                JOIN characters c ON sca.character_id = c.id
                WHERE sca.scene_id = :sid
            """), {"sid": s.id}).fetchall()
            print(f"  Character Actions: {', '.join([f'{a.char_name}:{a.name}({a.weight})' for a in actions])}")

if __name__ == "__main__":
    get_scene_tags(416)
