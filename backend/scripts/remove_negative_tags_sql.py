"""Remove problematic tags from character negative prompts using raw SQL."""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

TAGS_TO_REMOVE = ["cropped", "head out of frame", "out of frame"]


def main():
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        # First, show current state
        print("Current state:")
        print("=" * 80)
        cur.execute("""
            SELECT id, name, recommended_negative
            FROM characters
            WHERE recommended_negative IS NOT NULL
            ORDER BY id
        """)

        for row in cur.fetchall():
            char_id, name, negative = row
            print(f"{char_id}. {name}: {negative}")
        print()

        # Update: remove problematic tags
        print("Removing tags:", TAGS_TO_REMOVE)
        print("=" * 80)

        cur.execute("""
            UPDATE characters
            SET recommended_negative = (
                SELECT array_agg(tag)
                FROM unnest(recommended_negative) AS tag
                WHERE tag NOT IN ('cropped', 'head out of frame', 'out of frame')
            )
            WHERE recommended_negative IS NOT NULL
        """)

        rows_updated = cur.rowcount
        print(f"✓ Updated {rows_updated} rows")
        print()

        # Show new state
        print("New state:")
        print("=" * 80)
        cur.execute("""
            SELECT id, name, recommended_negative
            FROM characters
            WHERE recommended_negative IS NOT NULL
            ORDER BY id
        """)

        for row in cur.fetchall():
            char_id, name, negative = row
            print(f"{char_id}. {name}: {negative}")

        # Commit changes
        conn.commit()
        print()
        print(f"✅ Successfully removed tags from {rows_updated} characters")

    except Exception as exc:
        conn.rollback()
        print(f"❌ Error: {exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
