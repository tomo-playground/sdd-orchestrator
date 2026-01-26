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
        project_name = "conflict_test"

        # Clear existing test data
        cur.execute("DELETE FROM generation_logs WHERE project_name = %s", (project_name,))
        print(f"Cleared existing test data for project '{project_name}'")

        logs = []

        # Conflict pattern 1: upper body + full body (10 fails)
        for i in range(10, 20):
            logs.append({
                "project_name": project_name,
                "scene_index": i,
                "prompt": "1girl, sitting, upper body, full body, classroom",
                "tags": ["1girl", "sitting", "upper body", "full body", "classroom"],
                "status": "fail",
                "match_rate": 0.45,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 12345,
            })

        # Conflict pattern 2: indoors + outdoors (8 fails)
        for i in range(20, 28):
            logs.append({
                "project_name": project_name,
                "scene_index": i,
                "prompt": "1girl, standing, indoors, outdoors, city",
                "tags": ["1girl", "standing", "indoors", "outdoors", "city"],
                "status": "fail",
                "match_rate": 0.40,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 12346,
            })

        # Conflict pattern 3: day + night (7 fails)
        for i in range(30, 37):
            logs.append({
                "project_name": project_name,
                "scene_index": i,
                "prompt": "landscape, day, night, dramatic",
                "tags": ["landscape", "day", "night", "dramatic"],
                "status": "fail",
                "match_rate": 0.35,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 12347,
            })

        # Success cases (3 successes, no conflicts)
        for i in range(40, 43):
            logs.append({
                "project_name": project_name,
                "scene_index": i,
                "prompt": "1girl, sitting, upper body, classroom",
                "tags": ["1girl", "sitting", "upper body", "classroom"],
                "status": "success",
                "match_rate": 0.85,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 12348,
            })

        print(f"\nCreating {len(logs)} test generation logs...")
        print("  - 10 logs with 'upper body + full body' conflict (fail)")
        print("  - 8 logs with 'indoors + outdoors' conflict (fail)")
        print("  - 7 logs with 'day + night' conflict (fail)")
        print("  - 3 logs without conflicts (success)")
        print()

        # Insert logs
        for log in logs:
            cur.execute("""
                INSERT INTO generation_logs (
                    project_name, scene_index, prompt, tags, sd_params,
                    match_rate, status, seed
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                log["project_name"],
                log["scene_index"],
                log["prompt"],
                json.dumps(log["tags"]),
                json.dumps(log["sd_params"]),
                log["match_rate"],
                log["status"],
                log["seed"],
            ))

        conn.commit()
        print(f"✅ Created {len(logs)} test logs in project '{project_name}'")
        print()
        print("Next steps:")
        print(f"  1. curl 'http://localhost:8000/generation-logs/suggest-conflict-rules?project_name={project_name}&min_occurrences=5&fail_rate_threshold=0.6'")
        print("  2. Review suggested rules")
        print("  3. Apply rules via POST /generation-logs/apply-conflict-rules")

    except Exception as exc:
        conn.rollback()
        print(f"❌ Error: {exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
