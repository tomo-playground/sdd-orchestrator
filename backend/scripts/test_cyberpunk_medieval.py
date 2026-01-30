"""Test applying a truly new conflict rule: cyberpunk + medieval."""

import json
import os

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
API_BASE = "http://localhost:8000"


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        project_name = "cyberpunk_medieval_test"

        # Ensure tags exist in tags table
        print("Ensuring tags exist in DB...")
        for tag_name in ["cyberpunk", "medieval", "fantasy", "city", "castle"]:
            cur.execute("""
                INSERT INTO tags (name, category, priority)
                VALUES (%s, 'general', 5)
                ON CONFLICT (name) DO NOTHING
            """, (tag_name,))
        conn.commit()
        print("✅ Tags ensured\n")

        # Clear existing data
        cur.execute("DELETE FROM generation_logs WHERE project_name = %s", (project_name,))

        logs = []

        # Conflict: cyberpunk + medieval (10 fails)
        for i in range(100, 110):
            logs.append({
                "project_name": project_name,
                "scene_index": i,
                "prompt": "1girl, cyberpunk, medieval, fantasy",
                "tags": ["1girl", "cyberpunk", "medieval", "fantasy"],
                "status": "fail",
                "match_rate": 0.35,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 88888,
            })

        # Success: just cyberpunk (3 successes)
        for i in range(110, 113):
            logs.append({
                "project_name": project_name,
                "scene_index": i,
                "prompt": "1girl, cyberpunk, city",
                "tags": ["1girl", "cyberpunk", "city"],
                "status": "success",
                "match_rate": 0.90,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 88887,
            })

        # Success: just medieval (3 successes)
        for i in range(113, 116):
            logs.append({
                "project_name": project_name,
                "scene_index": i,
                "prompt": "1girl, medieval, castle",
                "tags": ["1girl", "medieval", "castle"],
                "status": "success",
                "match_rate": 0.88,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 88886,
            })

        print(f"Creating {len(logs)} test logs...")
        print("  - 10 fails with 'cyberpunk + medieval'")
        print("  - 3 successes with 'cyberpunk' only")
        print("  - 3 successes with 'medieval' only")
        print()

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
        print(f"✅ Created {len(logs)} logs\n")

        # Get suggestions
        print("Step 1: Getting conflict rule suggestions...")
        response = requests.get(
            f"{API_BASE}/generation-logs/suggest-conflict-rules",
            params={
                "project_name": project_name,
                "min_occurrences": 5,
                "fail_rate_threshold": 0.8
            }
        )

        if response.status_code != 200:
            print(f"❌ Suggest failed: {response.status_code}")
            print(response.text)
            return

        result = response.json()
        print(f"Found {result['new_rules_count']} new suggestions\n")

        # Find cyberpunk + medieval
        target_rule = None
        for rule in result["suggested_rules"]:
            if {rule["tag1"], rule["tag2"]} == {"cyberpunk", "medieval"}:
                target_rule = rule
                break

        if not target_rule:
            print("❌ 'cyberpunk + medieval' not in suggestions")
            print("\nAll suggestions:")
            for rule in result["suggested_rules"][:10]:
                print(f"  - {rule['tag1']} + {rule['tag2']} ({rule['fail_rate']*100:.0f}% fail rate)")
            return

        print("✅ Found 'cyberpunk + medieval' conflict:")
        print(f"  Co-occurrence: {target_rule['co_occurrence']}")
        print(f"  Fail count: {target_rule['fail_count']}")
        print(f"  Fail rate: {target_rule['fail_rate']*100:.0f}%")
        print(f"  Avg match rate: {target_rule['avg_match_rate']}")
        print(f"  Reason: {target_rule['reason']}")
        print()

        # Apply it
        print("Step 2: Applying rule to database...")
        apply_response = requests.post(
            f"{API_BASE}/generation-logs/apply-conflict-rules",
            json={"rules": [{"tag1": "cyberpunk", "tag2": "medieval"}]}
        )

        if apply_response.status_code != 200:
            print(f"❌ Apply failed: {apply_response.status_code}")
            print(apply_response.text)
            return

        apply_result = apply_response.json()
        print("✅ Apply result:")
        print(f"  Applied: {apply_result['applied_count']} rules")
        print(f"  Skipped: {apply_result['skipped_count']} rules")
        if apply_result.get("details"):
            for detail in apply_result["details"]:
                status = detail.get("status", "unknown")
                reason = detail.get("reason", "")
                print(f"  - {detail['tag1']} + {detail['tag2']}: {status}" + (f" ({reason})" if reason else ""))
        print()

        if apply_result["applied_count"] > 0:
            print("Step 3: Verifying in database...")
            cur.execute("""
                SELECT t1.name as tag1, t2.name as tag2
                FROM tag_rules tr
                JOIN tags t1 ON tr.source_tag_id = t1.id
                JOIN tags t2 ON tr.target_tag_id = t2.id
                WHERE tr.rule_type = 'conflict'
                  AND (
                    (t1.name = 'cyberpunk' AND t2.name = 'medieval')
                    OR (t1.name = 'medieval' AND t2.name = 'cyberpunk')
                  )
            """)
            rows = cur.fetchall()
            print(f"✅ Found {len(rows)} rules in DB:")
            for row in rows:
                print(f"  - {row[0]} → {row[1]}")
            print()
            print("🎉 Task #5 (Conflict Rule Auto-Discovery) COMPLETE!")
        else:
            print("⚠️ No rules were applied")

    except Exception as exc:
        conn.rollback()
        print(f"❌ Error: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
