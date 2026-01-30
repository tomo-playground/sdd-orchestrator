"""Create test generation logs with conflict patterns using raw SQL."""

import json
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        # Create a test storyboard
        cur.execute("""
            INSERT INTO storyboards (title, description, created_at, updated_at)
            VALUES (%s, %s, NOW(), NOW())
            RETURNING id
        """, ("Conflict Test SQL", "Temporary storyboard for SQL test script"))
        storyboard_id = cur.fetchone()[0]
        print(f"Created temporary storyboard ID: {storyboard_id}")

        logs = []

        # Conflict pattern 1: upper body + full body (10 fails)
        for i in range(10, 20):
            logs.append({
                "storyboard_id": storyboard_id,
                "scene_id": i,
                "prompt": "1girl, sitting, upper body, full body, classroom",
                "tags_used": ["1girl", "sitting", "upper body", "full body", "classroom"],
                "status": "fail",
                "match_rate": 0.45,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 12345,
            })

        # Conflict pattern 2: indoors + outdoors (8 fails)
        for i in range(20, 28):
            logs.append({
                "storyboard_id": storyboard_id,
                "scene_id": i,
                "prompt": "1girl, standing, indoors, outdoors, city",
                "tags_used": ["1girl", "standing", "indoors", "outdoors", "city"],
                "status": "fail",
                "match_rate": 0.40,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 12346,
            })

        # Conflict pattern 3: day + night (7 fails)
        for i in range(30, 37):
            logs.append({
                "storyboard_id": storyboard_id,
                "scene_id": i,
                "prompt": "landscape, day, night, dramatic",
                "tags_used": ["landscape", "day", "night", "dramatic"],
                "status": "fail",
                "match_rate": 0.35,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 12347,
            })

        # Success cases (3 successes, no conflicts)
        for i in range(40, 43):
            logs.append({
                "storyboard_id": storyboard_id,
                "scene_id": i,
                "prompt": "1girl, sitting, upper body, classroom",
                "tags_used": ["1girl", "sitting", "upper body", "classroom"],
                "status": "success",
                "match_rate": 0.85,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 12348,
            })

        print(f"\nCreating {len(logs)} test activity logs...")
        print("  - 10 logs with 'upper body + full body' conflict (fail)")
        print("  - 8 logs with 'indoors + outdoors' conflict (fail)")
        print("  - 7 logs with 'day + night' conflict (fail)")
        print("  - 3 logs without conflicts (success)")
        print()

        # Insert logs
        for log in logs:
            cur.execute("""
                INSERT INTO activity_logs (
                    storyboard_id, scene_id, prompt, tags_used, sd_params,
                    match_rate, status, seed, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                log["storyboard_id"],
                log["scene_id"],
                log["prompt"],
                json.dumps(log["tags_used"]),
                json.dumps(log["sd_params"]),
                log["match_rate"],
                log["status"],
                log["seed"],
            ))

        conn.commit()
        print(f"✅ Created {len(logs)} test logs in storyboard {storyboard_id}")
        print()
        print("Next steps:")
        print(f"  1. curl 'http://localhost:8000/activity-logs/suggest-conflict-rules?storyboard_id={storyboard_id}&min_occurrences=5&fail_rate_threshold=0.6'")
        print("  2. Review suggested rules")
        print("  3. Apply rules via POST /activity-logs/apply-conflict-rules")
        print()
        print("Cleanup:")
        print("  Manually delete storyboard when done, or run scripts/cleanup_orphans.py")

    except Exception as exc:
        conn.rollback()
        print(f"❌ Error: {exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
