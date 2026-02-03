#!/usr/bin/env python3
"""전수 조사: ID 체계 일관성 검사.

모든 엔티티의 ID가 올바르게:
1. DB에 저장되는지
2. API 응답에 포함되는지
3. Frontend에서 사용되는지
확인합니다.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import os  # noqa: E402

import psycopg2  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(backend_dir / ".env")

def check_entity_ids():
    """Check ID consistency across entities."""
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))

    entities = {
        "storyboards": {"pk": "id", "refs": []},
        "scenes": {"pk": "id", "refs": ["storyboard_id"]},
        "characters": {"pk": "id", "refs": []},
        "tags": {"pk": "id", "refs": []},
        "loras": {"pk": "id", "refs": []},
        "style_profiles": {"pk": "id", "refs": []},
        "activity_logs": {"pk": "id", "refs": ["storyboard_id", "scene_id", "character_id"]},
        "prompt_histories": {"pk": "id", "refs": ["character_id"]},
        "scene_tags": {"pk": None, "refs": ["scene_id", "tag_id"]},
        "scene_character_actions": {"pk": None, "refs": ["scene_id", "character_id"]},
    }

    print("=" * 80)
    print("ID CONSISTENCY AUDIT")
    print("=" * 80)

    with conn.cursor() as cur:
        for table, info in entities.items():
            print(f"\n📋 Table: {table}")
            print("-" * 40)

            # Check if table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                )
            """, (table,))

            if not cur.fetchone()[0]:
                print("  ⚠️  Table does not exist")
                continue

            # Check primary key
            if info["pk"]:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s AND column_name = %s
                """, (table, info["pk"]))

                pk_info = cur.fetchone()
                if pk_info:
                    print(f"  ✓ PK: {pk_info[0]} ({pk_info[1]}, nullable={pk_info[2]})")
                else:
                    print(f"  ❌ PK '{info['pk']}' not found")

            # Check foreign keys
            for fk in info["refs"]:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s AND column_name = %s
                """, (table, fk))

                fk_info = cur.fetchone()
                if fk_info:
                    nullable = "nullable" if fk_info[2] == "YES" else "NOT NULL"
                    print(f"  ✓ FK: {fk_info[0]} ({fk_info[1]}, {nullable})")
                else:
                    print(f"  ❌ FK '{fk}' not found")

            # Check record count
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  📊 Records: {count}")

            # Check for NULL IDs (if PK exists)
            if info["pk"]:
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {info['pk']} IS NULL")
                null_count = cur.fetchone()[0]
                if null_count > 0:
                    print(f"  ⚠️  NULL {info['pk']}: {null_count} records")

            # Check for NULL FKs
            for fk in info["refs"]:
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {fk} IS NULL")
                null_count = cur.fetchone()[0]
                if null_count > 0:
                    print(f"  📝 NULL {fk}: {null_count} records (may be intentional)")

    conn.close()

    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("""
1. All primary keys should be NOT NULL
2. Foreign keys should be NOT NULL unless optional by design
3. Check API serializers return 'id' field for all entities
4. Frontend should use DB IDs, not array indices
5. Activity logs should reference actual entity IDs, not indices
    """)

if __name__ == "__main__":
    check_entity_ids()
