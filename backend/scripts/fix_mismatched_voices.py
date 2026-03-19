import random
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import VoicePreset

# Data map for updates
# Format: voice_id: (new_name, new_desc, new_voice_design_prompt)
UPDATES = {
    # Gunwoo (13): Currently high tenor, exaggerated. Need calm, professional 20s male.
    13: (
        "건우",
        "20대후반 남성 — 차분하고 지적인 스마트한 목소리, 신뢰감 주는 중저음",
        "A young man in his late 20s with a calm, intelligent, and professional voice. He speaks at a moderate pace with clear, precise articulation. His tone is reliable, trustworthy, and composed, suited for business or formal settings. He sounds confident but approachable, with a smooth mid-low pitch.",
    ),
    # Hyunseo (16) -> Midori: Currently 50s female. Need passionate, energetic teen boy.
    16: (
        "미도리 (소년)",
        "10대후반 남성 — 열정적이고 활기찬 소년 영웅, 에너지 넘치는 목소리",
        "A teenage boy with a passionate, energetic, and slightly breathless voice. He speaks at a fast pace with a sense of urgency and determination. His pitch is mid-to-high, typical of an adolescent hero who never gives up. He places strong emotional emphasis on his words, sounding brave and earnest.",
    ),
    # Sion (18): Currently 30s cynical baritone. Need energetic Ghibli boy.
    18: (
        "시온",
        "10대 중반 소년 — 지브리 스타일의 호기심 많고 맑은 미소년 목소리",
        "A young teenage boy around 14 years old with a clear, bright, and innocent voice. He speaks with lively curiosity and gentle enthusiasm. His tone is pure and uncorrupted, like a protagonist in a classic Ghibli movie. He sounds adventurous but kind-hearted, with a light and airy vocal quality.",
    ),
    # Doyun (20) - Ensure he sounds like a clean, logical 20s male instead of 30s thriller bass
    20: (
        "도윤",
        "20대후반 남성 — 깔끔하고 단정한 이성적인 아나운서 톤, 차분한 속도",
        "A man in his late 20s with a clean, neat, and highly rational voice. He speaks at a measured, calm pace, taking careful pauses. His tone is logical, objective, and slightly detached, resembling a professional news anchor. His pronunciation is flawless and crisp without unnecessary emotional fluctuation. Mid-range pitch, very stable.",
    ),
    # Rina/Yuna (19) - Ensure she sounds elegant and calm for Yuna instead of punchy esports caster
    19: (
        "유나",
        "20대중반 여성 — 우아하고 기품 있는 차분한 목소리, 부드러운 아나운서 톤",
        "A woman in her mid-20s with an elegant, graceful, and serene voice. She speaks at a calm, deliberate pace with flowing intonation. Her tone is refined and sophisticated, conveying a sense of gentle dignity. She sounds warm but impeccably polite, with clear and beautiful pronunciation. Mid-range pitch, soothing and classy.",
    ),
}


def main():
    db = SessionLocal()
    try:
        updated_count = 0
        for vid, (new_name, new_desc, new_design) in UPDATES.items():
            voice = db.query(VoicePreset).filter(VoicePreset.id == vid).first()
            if voice:
                voice.name = new_name
                voice.description = new_desc
                voice.voice_design_prompt = new_design
                # Generate a new random seed for the new voice persona
                voice.voice_seed = random.randint(10000000, 999999999)
                updated_count += 1
                print(f"✅ Updated Voice ID {vid}: {new_name}")
            else:
                print(f"⚠️ Voice ID {vid} not found.")

        db.commit()
        print(f"\n🎉 Successfully updated {updated_count} voice presets.")

    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
