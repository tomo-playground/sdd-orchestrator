"""Test applying a new conflict rule that doesn't exist yet."""

import os
import psycopg2
import json
import requests
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
API_BASE = "http://localhost:8000"


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        project_name = "new_conflict_test"

        # Clear existing data
        cur.execute("DELETE FROM generation_logs WHERE project_name = %s", (project_name,))

        # Create logs with "sitting + standing" conflict (doesn't exist in DB yet)
        logs = []

        # Conflict: sitting + standing (8 fails)
        for i in range(50, 58):
            logs.append({
                "project_name": project_name,
                "scene_index": i,
                "prompt": "1girl, sitting, standing, park",
                "tags": ["1girl", "sitting", "standing", "park"],
                "status": "fail",
                "match_rate": 0.38,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 99999,
            })

        # Success: just sitting (3 successes)
        for i in range(60, 63):
            logs.append({
                "project_name": project_name,
                "scene_index": i,
                "prompt": "1girl, sitting, park",
                "tags": ["1girl", "sitting", "park"],
                "status": "success",
                "match_rate": 0.88,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 99998,
            })

        print(f"Creating {len(logs)} test logs with 'sitting + standing' conflict...")

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
        print(f"✅ Created {len(logs)} logs")
        print()

        # Get suggestions
        print("Getting conflict rule suggestions...")
        response = requests.get(
            f"{API_BASE}/generation-logs/suggest-conflict-rules",
            params={
                "project_name": project_name,
                "min_occurrences": 5,
                "fail_rate_threshold": 0.7
            }
        )

        if response.status_code == 200:
            result = response.json()
            print(f"Found {result['new_rules_count']} new suggestions")

            # Find sitting + standing
            sitting_standing = None
            for rule in result["suggested_rules"]:
                if set([rule["tag1"], rule["tag2"]]) == {"sitting", "standing"}:
                    sitting_standing = rule
                    break

            if sitting_standing:
                print("\n✅ Found 'sitting + standing' conflict:")
                print(json.dumps(sitting_standing, indent=2))
                print()

                # Apply it
                print("Applying rule...")
                apply_response = requests.post(
                    f"{API_BASE}/generation-logs/apply-conflict-rules",
                    json={"rules": [{"tag1": "sitting", "tag2": "standing"}]}
                )

                if apply_response.status_code == 200:
                    apply_result = apply_response.json()
                    print("✅ Apply result:")
                    print(json.dumps(apply_result, indent=2))
                else:
                    print(f"❌ Apply failed: {apply_response.status_code}")
                    print(apply_response.text)
            else:
                print("❌ 'sitting + standing' not in suggestions")
                print("All suggestions:")
                print(json.dumps(result["suggested_rules"], indent=2))
        else:
            print(f"❌ Suggest failed: {response.status_code}")
            print(response.text)

    except Exception as exc:
        conn.rollback()
        print(f"❌ Error: {exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
