"""채널 초기 데이터 세팅: 기존 테스트 데이터 삭제 → 새 그룹/캐릭터 생성."""

import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import psycopg2


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # ============================================================
        # 1단계: 삭제
        # ============================================================
        print("=== 1단계: 삭제 ===")

        # 1-1. render_history (storyboard CASCADE 안 되므로 먼저 삭제)
        cur.execute("DELETE FROM render_history WHERE storyboard_id IN (1089, 1090)")
        print(f"  render_history 삭제: {cur.rowcount}건")

        # 1-2. scenes (CASCADE: scene_character_actions, scene_tags 자동)
        cur.execute("DELETE FROM scenes WHERE storyboard_id IN (1089, 1090)")
        print(f"  scenes 삭제: {cur.rowcount}건")

        # 1-3. storyboard_characters (스토리보드 기준)
        cur.execute(
            "DELETE FROM storyboard_characters "
            "WHERE storyboard_id IN (1089, 1090)"
        )
        print(f"  storyboard_characters 삭제: {cur.rowcount}건")

        # 1-4. storyboards
        cur.execute("DELETE FROM storyboards WHERE id IN (1089, 1090)")
        print(f"  storyboards 삭제: {cur.rowcount}건")

        # 1-6. character_tags — 해당 그룹의 모든 캐릭터 (soft-deleted 포함)
        cur.execute(
            "DELETE FROM character_tags WHERE character_id IN "
            "(SELECT id FROM characters WHERE group_id BETWEEN 14 AND 19)"
        )
        print(f"  character_tags 삭제: {cur.rowcount}건")

        # 1-7. storyboard_characters — 그룹 소속 캐릭터 참조 정리
        cur.execute(
            "DELETE FROM storyboard_characters WHERE character_id IN "
            "(SELECT id FROM characters WHERE group_id BETWEEN 14 AND 19)"
        )
        print(f"  storyboard_characters(캐릭터) 삭제: {cur.rowcount}건")

        # 1-8. activity_logs — 그룹 소속 캐릭터 NULL 처리
        cur.execute(
            "UPDATE activity_logs SET character_id = NULL "
            "WHERE character_id IN "
            "(SELECT id FROM characters WHERE group_id BETWEEN 14 AND 19)"
        )
        print(f"  activity_logs(캐릭터) NULL 처리: {cur.rowcount}건")

        # 1-9. characters — 그룹 소속 전체 (soft-deleted 포함)
        cur.execute("DELETE FROM characters WHERE group_id BETWEEN 14 AND 19")
        print(f"  characters 삭제: {cur.rowcount}건")

        # 1-10. groups
        cur.execute("DELETE FROM groups WHERE id BETWEEN 14 AND 19")
        print(f"  groups 삭제: {cur.rowcount}건")

        # ============================================================
        # 2단계: 새 그룹 생성
        # ============================================================
        print("\n=== 2단계: 새 그룹 생성 ===")

        groups = [
            ("오늘도 출근했습니다", "직장인 공감 채널. 자조적 유머와 공감 에피소드", 3),
            ("급식시간", "중고생 문화 채널. 밈 감성의 학교생활 이야기", 10),
            ("역사 안 주무셨죠", "역사 채널. 현대 언어로 풀어내는 역사 뒷이야기", 7),
        ]

        group_ids = {}
        for name, desc, style_id in groups:
            cur.execute(
                "INSERT INTO groups (project_id, name, description, style_profile_id) "
                "VALUES (7, %s, %s, %s) RETURNING id",
                (name, desc, style_id),
            )
            gid = cur.fetchone()[0]
            group_ids[name] = gid
            print(f"  그룹 생성: #{gid} {name} (style_profile_id={style_id})")

        # ============================================================
        # 3단계: 새 캐릭터 생성
        # ============================================================
        print("\n=== 3단계: 새 캐릭터 생성 ===")

        characters = [
            # (group_key, name, gender, description, positive, negative, voice_id, ip_model)
            (
                "오늘도 출근했습니다",
                "하은",
                "female",
                "2년차 사원. 성실하지만 매일 퇴근만 기다린다. 속마음이 터지는 독백 담당. 피곤하지만 귀여운 매력.",
                "1girl, young_woman, brown_hair, ponytail, hair_tie, tired_eyes, brown_eyes, office_lady, cardigan, beige_cardigan, white_blouse, id_card, lanyard, pencil_skirt, black_skirt, tumbler, flat_color",
                "detailed_background, gradient, shadow, 3d, realistic",
                24,
                "clip_face",
            ),
            (
                "오늘도 출근했습니다",
                "재민",
                "male",
                "5년차 팀장. 일 잘하지만 말이 많다. 하은에게 현실 조언과 잔소리를 동시에 하는 선배.",
                "1boy, young_man, black_hair, short_hair, glasses, rectangular_glasses, brown_eyes, necktie, loose_necktie, dress_shirt, white_shirt, sleeves_rolled_up, slacks, coffee_cup, flat_color",
                "detailed_background, gradient, shadow, 3d, realistic",
                13,
                "clip_face",
            ),
            (
                "급식시간",
                "도현",
                "male",
                '만물박사인데 절반은 틀리는 훈수 남고생. "이거 알아?"로 시작하는 TMI 폭격기.',
                "1boy, male_focus, brown_hair, short_hair, hairband, school_uniform, blazer, blue_blazer, white_shirt, plaid_necktie, black_pants, earphones, one_earphone_removed, hands_in_pockets",
                "realistic, photorealistic, 3d",
                16,
                "clip_face",
            ),
            (
                "급식시간",
                "서연",
                "female",
                "한마디로 팩트 정리하는 여고생. 도현이 틀릴 때 표정이 하이라이트.",
                "1girl, female_focus, black_hair, short_hair, bob_cut, hair_clip, hairpin, brown_eyes, school_uniform, cardigan, pink_cardigan, sailor_collar, pleated_skirt, navy_skirt, holding_phone, smartphone",
                "realistic, photorealistic, 3d",
                10,
                "clip_face",
            ),
            (
                "역사 안 주무셨죠",
                "준서",
                "male",
                "역사 덕후 대학생 진행자. 반말 섞인 친근한 해설. 고정 출연.",
                "1boy, young_man, black_hair, messy_hair, glasses, round_eyewear, brown_eyes, hoodie, grey_hoodie, casual, open_book, notebook",
                "chibi, super_deformed, flat_color",
                13,
                "clip_face",
            ),
            (
                "역사 안 주무셨죠",
                "이순신",
                "male",
                "역사 인물 베이스. 매회 다른 역사 인물로 복장만 교체. 현대어로 대답하는 역할.",
                "1boy, mature_male, black_hair, topknot, facial_hair, goatee, sharp_eyes, brown_eyes, hanbok, traditional_clothes, armor, korean_armor, serious",
                "chibi, super_deformed, flat_color, modern_clothes",
                9,
                "clip_face",
            ),
            (
                "역사 안 주무셨죠",
                "세종대왕",
                "male",
                "역사 인물. 학자군주의 인자한 모습. 현대어로 대답.",
                "1boy, mature_male, black_hair, topknot, beard, gentle_eyes, brown_eyes, hanbok, royal_hanbok, gonryongpo, traditional_clothes, sitting, wise",
                "chibi, super_deformed, flat_color, modern_clothes",
                9,
                "clip_face",
            ),
        ]

        for (
            group_key,
            name,
            gender,
            desc,
            pos,
            neg,
            voice_id,
            ip_model,
        ) in characters:
            gid = group_ids[group_key]
            cur.execute(
                "INSERT INTO characters "
                "(group_id, name, gender, description, positive_prompt, "
                "negative_prompt, voice_preset_id, ip_adapter_model) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (gid, name, gender, desc, pos, neg, voice_id, ip_model),
            )
            cid = cur.fetchone()[0]
            print(f"  캐릭터 생성: #{cid} {name} (group={group_key})")

        conn.commit()
        print("\n=== 완료: 트랜잭션 커밋 성공 ===")

    except Exception as e:
        conn.rollback()
        print(f"\n!!! 에러 발생, 롤백: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
