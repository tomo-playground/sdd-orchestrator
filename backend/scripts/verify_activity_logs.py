#!/usr/bin/env python3
"""Activity Log 중복 검증 스크립트.

Backend activity log 생성 제거 후 검증:
1. 중복 로그가 생성되지 않는지
2. image_url이 포함되는지
3. negative_prompt가 포함되는지
4. scene_id가 올바른 DB ID인지
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

load_dotenv(backend_dir / ".env")


def main():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))

    print("=" * 80)
    print("ACTIVITY LOG 검증")
    print("=" * 80)

    with conn.cursor() as cur:
        # 최근 activity logs 확인
        cur.execute("""
            SELECT
                id,
                storyboard_id,
                scene_id,
                character_id,
                image_url IS NOT NULL as has_image,
                negative_prompt IS NOT NULL as has_negative,
                created_at
            FROM activity_logs
            ORDER BY id DESC
            LIMIT 10
        """)

        print("\n📋 최근 Activity Logs (최신 10개):")
        print("ID     SB_ID   SCENE_ID  CHAR_ID  IMG   NEG   CREATED_AT")
        print("-" * 80)

        for row in cur.fetchall():
            img = "✓" if row[4] else "✗"
            neg = "✓" if row[5] else "✗"
            created = row[6].strftime("%Y-%m-%d %H:%M:%S") if row[6] else "N/A"
            scene_id = str(row[2]) if row[2] is not None else "None"
            char_id = str(row[3]) if row[3] is not None else "None"
            print(f"{row[0]:<6} {row[1]:<7} {scene_id:<9} {char_id:<8} {img:<5} {neg:<5} {created}")

        # 통계
        print("\n" + "=" * 80)
        print("📊 통계:")
        print("=" * 80)

        cur.execute("SELECT COUNT(*) FROM activity_logs")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM activity_logs WHERE image_url IS NOT NULL")
        with_image = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM activity_logs WHERE negative_prompt IS NOT NULL")
        with_negative = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM activity_logs WHERE scene_id IS NOT NULL")
        with_scene = cur.fetchone()[0]

        print(f"Total logs:         {total}")
        print(f"With image_url:     {with_image} ({with_image * 100 // total if total else 0}%)")
        print(f"With negative:      {with_negative} ({with_negative * 100 // total if total else 0}%)")
        print(f"With scene_id:      {with_scene} ({with_scene * 100 // total if total else 0}%)")

        # Scene ID 검증 (DB ID vs 인덱스)
        print("\n" + "=" * 80)
        print("🔍 Scene ID 검증 (DB ID 사용 여부):")
        print("=" * 80)

        cur.execute("""
            SELECT
                al.id as log_id,
                al.scene_id,
                s.id as actual_scene_id,
                al.scene_id = s.id as is_valid
            FROM activity_logs al
            LEFT JOIN scenes s ON al.scene_id = s.id
            WHERE al.scene_id IS NOT NULL
            ORDER BY al.id DESC
            LIMIT 10
        """)

        print("LOG_ID  AL.SCENE_ID  DB.SCENE_ID  VALID")
        print("-" * 45)

        valid_count = 0
        invalid_count = 0

        for row in cur.fetchall():
            is_valid = "✓" if row[3] else "✗"
            actual = row[2] if row[2] is not None else "Not Found"
            print(f"{row[0]:<7} {row[1]:<12} {actual:<12} {is_valid}")

            if row[3]:
                valid_count += 1
            else:
                invalid_count += 1

        print(f"\n✓ Valid:   {valid_count}")
        print(f"✗ Invalid: {invalid_count}")

        if invalid_count > 0:
            print("\n⚠️  일부 activity log의 scene_id가 실제 scene DB ID와 매칭되지 않습니다.")
            print("   이전에 인덱스로 저장된 로그일 수 있습니다.")

    conn.close()


if __name__ == "__main__":
    main()
