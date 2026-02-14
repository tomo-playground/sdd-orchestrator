from sqlalchemy import text
from database import engine
import json

def analyze_tts(storyboard_id):
    with engine.connect() as conn:
        # 1. Storyboard info
        storyboard = conn.execute(
            text("SELECT id, title, group_id, language FROM storyboards WHERE id = :id"),
            {"id": storyboard_id}
        ).fetchone()
        
        if not storyboard:
            print(f"Storyboard {storyboard_id} not found.")
            return

        print(f"--- Storyboard Info ---")
        print(f"ID: {storyboard.id}")
        print(f"Title: {storyboard.title}")
        print(f"Group ID: {storyboard.group_id}")
        print(f"Language: {storyboard.language}")

        # 2. Group Config (Narrator Voice)
        group_config = conn.execute(
            text("""
                SELECT gc.narrator_voice_preset_id, vp.name as voice_name, vp.tts_engine, vp.voice_design_prompt
                FROM group_config gc
                LEFT JOIN voice_presets vp ON gc.narrator_voice_preset_id = vp.id
                WHERE gc.group_id = :group_id
            """),
            {"group_id": storyboard.group_id}
        ).fetchone()
        
        print(f"\n--- Narrator Voice config ---")
        if group_config:
            print(f"Narrator Voice Preset ID: {group_config.narrator_voice_preset_id}")
            print(f"Voice Name: {group_config.voice_name}")
            print(f"TTS Engine: {group_config.tts_engine}")
            print(f"Voice Design Prompt: {group_config.voice_design_prompt}")
        else:
            print("No group config found for this group.")

        # 3. Characters in Storyboard
        characters = conn.execute(
            text("""
                SELECT sc.speaker, c.name, c.gender, vp.name as voice_name, vp.tts_engine, vp.voice_design_prompt
                FROM storyboard_characters sc
                JOIN characters c ON sc.character_id = c.id
                LEFT JOIN voice_presets vp ON c.voice_preset_id = vp.id
                WHERE sc.storyboard_id = :id
            """),
            {"id": storyboard_id}
        ).fetchall()
        
        print(f"\n--- Characters Config ---")
        for char in characters:
            print(f"Speaker: {char.speaker}")
            print(f"Name: {char.name}")
            print(f"Gender: {char.gender}")
            print(f"Voice: {char.voice_name}")
            print(f"TTS Engine: {char.tts_engine}")
            print(f"Voice Design Prompt: {char.voice_design_prompt}")
            print("-" * 20)

        # 4. Scenes and Scripts
        scenes = conn.execute(
            text("""
                SELECT s.id as scene_id, s."order", s.speaker, s.script, s.duration, ma.storage_key, ma.id as asset_id
                FROM scenes s
                LEFT JOIN media_assets ma ON ma.owner_type = 'scene_audio' AND ma.owner_id = s.id
                WHERE s.storyboard_id = :id
                ORDER BY s."order"
            """),
            {"id": storyboard_id}
        ).fetchall()
        
        print(f"\n--- Scenes and TTS Assets ---")
        for scene in scenes:
            print(f"Scene {scene.order} | Speaker: {scene.speaker} | Duration: {scene.duration}")
            print(f"Script: {scene.script}")
            if scene.storage_key:
                print(f"TTS Audio: {scene.storage_key} (ID: {scene.asset_id})")
            else:
                print("TTS Audio: MISSING")
            print("-" * 10)

        # 5. Activity Logs
        logs = conn.execute(
            text("""
                SELECT status, prompt, created_at
                FROM activity_logs
                WHERE storyboard_id = :id
                ORDER BY created_at DESC
                LIMIT 10
            """),
            {"id": storyboard_id}
        ).fetchall()
        
        print(f"\n--- Recent Activity Logs ---")
        if logs:
            for log in logs:
                print(f"[{log.created_at}] Status: {log.status} | Prompt: {log.prompt[:50]}...")
        else:
            print("No activity logs found for this storyboard.")

if __name__ == "__main__":
    analyze_tts(416)
