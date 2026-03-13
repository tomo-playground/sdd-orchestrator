"""캐릭터별 외모 고정 태그(character_tags) 등록 스크립트."""

import sys
from pathlib import Path

# backend/ 디렉토리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import create_engine, text

from config import DATABASE_URL

# ── 캐릭터별 태그 정의 ──
CHARACTER_TAGS: dict[int, list[tuple[str, float]]] = {
    # 하은 (id: 35) — 2년차 여사원
    35: [
        ("1girl", 1.0),
        ("young_woman", 1.0),
        ("brown_hair", 1.2),
        ("ponytail", 1.2),
        ("hair_tie", 1.0),
        ("medium_hair", 1.0),
        ("brown_eyes", 1.0),
        ("tired_eyes", 1.0),
        ("cardigan", 1.0),
        ("white_blouse", 1.0),
        ("pencil_skirt", 1.0),
        ("black_skirt", 1.0),
        ("lanyard", 1.0),
        ("id_card", 1.0),
    ],
    # 재민 (id: 36) — 5년차 팀장
    36: [
        ("1boy", 1.0),
        ("young_man", 1.0),
        ("black_hair", 1.2),
        ("short_hair", 1.0),
        ("brown_eyes", 1.0),
        ("glasses", 1.2),
        ("necktie", 1.0),
        ("loose_necktie", 1.0),
        ("dress_shirt", 1.0),
        ("white_shirt", 1.0),
        ("sleeves_rolled_up", 1.0),
        ("slacks", 1.0),
    ],
    # 도현 (id: 37) — 훈수 남고생
    37: [
        ("1boy", 1.0),
        ("male_focus", 1.0),
        ("brown_hair", 1.2),
        ("short_hair", 1.0),
        ("hairband", 1.2),
        ("school_uniform", 1.2),
        ("blazer", 1.0),
        ("white_shirt", 1.0),
        ("plaid_necktie", 1.0),
        ("black_pants", 1.0),
        ("earphones", 1.0),
    ],
    # 서연 (id: 38) — 팩폭 여고생
    38: [
        ("1girl", 1.0),
        ("black_hair", 1.2),
        ("short_hair", 1.0),
        ("bob_cut", 1.2),
        ("hairpin", 1.0),
        ("brown_eyes", 1.0),
        ("school_uniform", 1.2),
        ("cardigan", 1.0),
        ("pink_cardigan", 1.0),
        ("sailor_collar", 1.0),
        ("pleated_skirt", 1.0),
        ("smartphone", 1.0),
    ],
    # 준서 (id: 39) — 역사덕후 대학생
    39: [
        ("1boy", 1.0),
        ("young_man", 1.0),
        ("black_hair", 1.2),
        ("messy_hair", 1.2),
        ("glasses", 1.2),
        ("round_eyewear", 1.0),
        ("brown_eyes", 1.0),
        ("hoodie", 1.0),
        ("grey_hoodie", 1.0),
        ("notebook", 1.0),
        ("open_book", 1.0),
    ],
    # 이순신 (id: 40) — 역사 인물
    40: [
        ("1boy", 1.0),
        ("mature_male", 1.0),
        ("black_hair", 1.2),
        ("topknot", 1.2),
        ("facial_hair", 1.0),
        ("goatee", 1.0),
        ("brown_eyes", 1.0),
        ("hanbok", 1.2),
        ("traditional_clothes", 1.0),
        ("armor", 1.0),
    ],
    # 세종대왕 (id: 41) — 역사 인물
    41: [
        ("1boy", 1.0),
        ("mature_male", 1.0),
        ("black_hair", 1.2),
        ("topknot", 1.2),
        ("beard", 1.0),
        ("brown_eyes", 1.0),
        ("hanbok", 1.2),
        ("traditional_clothes", 1.0),
    ],
}

CHARACTER_NAMES = {
    35: "하은",
    36: "재민",
    37: "도현",
    38: "서연",
    39: "준서",
    40: "이순신",
    41: "세종대왕",
}


def main() -> None:
    engine = create_engine(DATABASE_URL)

    with engine.begin() as conn:
        # 1) tags 테이블에서 name → id 매핑 로드
        rows = conn.execute(text("SELECT id, name FROM tags")).fetchall()
        tag_map: dict[str, int] = {row[1]: row[0] for row in rows}
        print(f"[INFO] tags 테이블에서 {len(tag_map)}개 태그 로드 완료")

        # 2) 기존 character_tags 삭제 (대상 캐릭터만)
        char_ids = list(CHARACTER_TAGS.keys())
        conn.execute(
            text("DELETE FROM character_tags WHERE character_id = ANY(:ids)"),
            {"ids": char_ids},
        )
        print(f"[INFO] 기존 character_tags 삭제 완료 (character_ids: {char_ids})")

        # 3) INSERT
        total = 0
        skipped: list[str] = []

        for char_id, tags in CHARACTER_TAGS.items():
            char_name = CHARACTER_NAMES[char_id]
            count = 0

            for tag_name, weight in tags:
                tid = tag_map.get(tag_name)
                if tid is None:
                    msg = f"  [WARNING] '{tag_name}' → tags 테이블에 없음 (캐릭터: {char_name})"
                    print(msg)
                    skipped.append(f"{char_name}/{tag_name}")
                    continue

                conn.execute(
                    text(
                        "INSERT INTO character_tags (character_id, tag_id, weight, is_permanent) "
                        "VALUES (:cid, :tid, :w, true)"
                    ),
                    {"cid": char_id, "tid": tid, "w": weight},
                )
                count += 1

            total += count
            print(f"  [{char_name} (id={char_id})] {count}개 태그 등록")

        print(f"\n[결과] 총 {total}개 태그 등록 완료")
        if skipped:
            print(f"[스킵] {len(skipped)}개: {', '.join(skipped)}")


if __name__ == "__main__":
    main()
