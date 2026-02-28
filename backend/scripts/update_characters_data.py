import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Character

# ID -> (New Description, New Voice ID)
UPDATES = {
    9: ("발랄하고 에너지 넘치는 마법소녀 스타일. 캐주얼한 복장을 즐겨입는다.", 10),
    8: ("예민해서 지치는 20대 후반 직장인. 별일 아닌 걸 알면서도 신경 쓰이고, 말 못하고 삼킨 말이 많다. 날카롭지만 섬세하고, 솔직하지만 상처받기 쉬운 성격.", 24),
    12: ("차분한 20대 후반 정장 스타일의 남성. 지적이고 프로페셔널한 인상을 준다.", 13),
    15: ("지브리 스타일 여성 캐릭터. 숲과 자연을 사랑하는 밝고 순수한 소녀.", 12),
    17: ("차분하고 우아한 분위기의 20대 한국 여성. 긴 웨이브 머리와 부드러운 갈색 눈이 매력 포인트.", 19),
    16: ("지브리 스타일 남성 캐릭터. 모험을 좋아하고 호기심 많은 활기찬 소년.", 18),
    19: ("부드럽고 따뜻한 인상의 여성. 검은 긴 웨이브 머리에 차분하고 다정한 성격을 지녔다.", 23),
    13: ("그림책에서 튀어나온 듯한 귀여운 초등학생 소녀. 엉뚱하고 상상력이 풍부하다.", 22),
    14: ("동화책 주인공 같은 장난꾸러기 초등학생 소년. 에너지가 넘치고 활발하다.", 21),
    18: ("깔끔하고 단정한 인상의 20대 한국 남성. 짧은 직모 검은 머리와 날카로운 눈매가 특징이며, 이성적이고 차분하다.", 20),
    3: ("포기를 모르는 열정적인 소년 영웅 스타일. 정의감이 투철하고 늘 활기차다.", 16),
}

def main():
    db = SessionLocal()
    try:
        updated_count = 0
        for char_id, (desc, voice_id) in UPDATES.items():
            char = db.query(Character).filter(Character.id == char_id).first()
            if char:
                char.description = desc
                char.voice_preset_id = voice_id
                updated_count += 1
                print(f"✅ Updated '{char.name}' (ID: {char.id})")
            else:
                print(f"⚠️ Character ID {char_id} not found.")
        
        db.commit()
        print(f"\n🎉 Successfully updated {updated_count} characters.")
    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
