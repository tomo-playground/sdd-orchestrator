import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from schemas import OverlaySettings, VideoRequest, VideoScene
from services.video.builder import create_video_task

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL)


async def trigger_demo():
    storyboard_id = 416
    with engine.connect() as conn:
        # Get storyboard info
        sb = conn.execute(text("SELECT * FROM storyboards WHERE id = :id"), {"id": storyboard_id}).fetchone()._mapping

        # Get scenes
        scenes_res = conn.execute(
            text("""
            SELECT s.*, ma.storage_key as image_url 
            FROM scenes s
            LEFT JOIN media_assets ma ON s.image_asset_id = ma.id
            WHERE s.storyboard_id = :id 
            ORDER BY s."order"
        """),
            {"id": storyboard_id},
        ).fetchall()

        video_scenes = []
        for i, s in enumerate(scenes_res):
            s_data = s._mapping
            prompt = ""

            # Simulated TTS Agent: Injecting Emotional Prompts (DISABLED for Auto-Gen Test)
            # order = s_data['order']
            # if order == 0: prompt = "Narrator sounding very annoyed and sneezy, complaining about pollen."
            # elif order == 1: prompt = "Narrator sounding exhausted and angry about the heat waves."
            # elif order == 2: prompt = "Narrator sounding melancholic and lonely among falling leaves."
            # elif order == 3: prompt = "Narrator sounding freezing and miserable in a blizzard."
            # elif order == 4: prompt = "Narrator shouting with intense frustration, fed up with everything."
            # elif order == 5: prompt = "Narrator sounding curious and searching for an answer."
            # elif order >= 6: prompt = "Narrator sounding blissfully happy and relaxed in a comfy indoor setting."

            # if order == 11:
            #     prompt = "Narrator sounding extremely satisfied, sighing with pure comfort: Ah~"

            video_scenes.append(
                VideoScene(
                    image_url=s_data["image_url"] if s_data["image_url"] else "https://via.placeholder.com/512x768",
                    script=s_data["script"],
                    speaker=s_data["speaker"] or "Narrator",
                    duration=s_data["duration"] or 3.0,
                    voice_design_prompt=prompt,
                )
            )

        request = VideoRequest(
            scenes=video_scenes,
            storyboard_id=sb["id"],
            storyboard_title=sb["title"],
            layout_style="post",
            is_scene_text_included=True,
            is_audio_ducking_enabled=True,
            bgm_volume=0.2,
            bgm_file="cheerful_lofi.mp3",  # Choosing a neutral background
            overlay_settings=OverlaySettings(
                channel_name="Story Lab", caption=sb["title"], avatar_key="default_avatar"
            ),
        )

        print(f"Triggering video generation for SB {storyboard_id}...")
        result = await create_video_task(request)
        print(f"Demo Video Generated: {result.get('video_url')}")
        return result


if __name__ == "__main__":
    asyncio.run(trigger_demo())
