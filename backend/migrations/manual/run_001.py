#!/usr/bin/env python3
"""Execute 001_make_storyboard_id_required.sql migration."""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment
load_dotenv(backend_dir / ".env")

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in .env")
        return 1

    sql_file = Path(__file__).parent / "001_make_storyboard_id_required.sql"
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        return 1

    print(f"📄 Reading SQL from: {sql_file}")
    sql_content = sql_file.read_text()

    # Parse DATABASE_URL
    # Format: postgresql://user:pass@host:port/dbname
    if not db_url.startswith("postgresql://"):
        print("❌ Invalid DATABASE_URL format")
        return 1

    print("🔗 Connecting to database...")

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False  # Manual transaction control

        with conn.cursor() as cur:
            print("\n" + "=" * 60)
            print("STEP 1: Check NULL records count")
            print("=" * 60)
            cur.execute("SELECT COUNT(*) FROM activity_logs WHERE storyboard_id IS NULL")
            null_count = cur.fetchone()[0]
            print(f"Found {null_count} records with NULL storyboard_id")

            if null_count > 0:
                print(f"\n⚠️  About to DELETE {null_count} records with NULL storyboard_id")
                # Auto-confirm in non-interactive mode
                auto_confirm = os.getenv("AUTO_CONFIRM", "false").lower() == "true"
                if not auto_confirm:
                    try:
                        response = input("Continue? [y/N]: ")
                        if response.lower() != 'y':
                            print("❌ Aborted by user")
                            conn.rollback()
                            return 1
                    except (EOFError, KeyboardInterrupt):
                        print("\n❌ Non-interactive mode: Set AUTO_CONFIRM=true to proceed")
                        conn.rollback()
                        return 1
                else:
                    print("Auto-confirming (AUTO_CONFIRM=true)")

            print("\n" + "=" * 60)
            print("STEP 2: Delete NULL records")
            print("=" * 60)
            cur.execute("DELETE FROM activity_logs WHERE storyboard_id IS NULL")
            deleted = cur.rowcount
            print(f"✓ Deleted {deleted} records")

            print("\n" + "=" * 60)
            print("STEP 3: Add NOT NULL constraint")
            print("=" * 60)
            cur.execute("ALTER TABLE activity_logs ALTER COLUMN storyboard_id SET NOT NULL")
            print("✓ Constraint added")

            print("\n" + "=" * 60)
            print("STEP 4: Verification")
            print("=" * 60)
            cur.execute("SELECT COUNT(*) FROM activity_logs WHERE storyboard_id IS NULL")
            verify_count = cur.fetchone()[0]
            print(f"NULL records after migration: {verify_count}")

            if verify_count == 0:
                conn.commit()
                print("\n✅ Migration completed successfully!")
                return 0
            else:
                conn.rollback()
                print(f"\n❌ Verification failed: {verify_count} NULL records still exist")
                return 1

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
        return 1
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        if 'conn' in locals():
            conn.rollback()
        return 1
    finally:
        if 'conn' in locals():
            conn.close()
            print("🔌 Connection closed")

if __name__ == "__main__":
    sys.exit(main())
