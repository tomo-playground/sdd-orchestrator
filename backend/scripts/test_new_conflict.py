"""Test applying a new conflict rule using Storyboard Architecture."""

import json
import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from dotenv import load_dotenv
from database import SessionLocal
from models.storyboard import Storyboard
from models.activity_log import ActivityLog
from sqlalchemy import text

load_dotenv()
API_BASE = "http://localhost:8000"

def main():
    db = SessionLocal()
    storyboard_id = None
    
    try:
        # 1. Create Test Storyboard
        print("Creating test storyboard...")
        sb = Storyboard(title="Test Conflict Rules", description="Temporary storyboard for testing conflict detection")
        db.add(sb)
        db.commit()
        db.refresh(sb)
        storyboard_id = sb.id
        print(f"✅ Created Storyboard ID: {storyboard_id}")

        # 2. Create logs with "sitting + standing" conflict
        logs = []

        # Conflict: sitting + standing (8 fails)
        for i in range(50, 58):
            logs.append({
                "storyboard_id": storyboard_id,
                "scene_id": i,
                "prompt": "1girl, running, sleeping, park",
                "tags_used": ["1girl", "running", "sleeping", "park"],
                "status": "fail",
                "match_rate": 0.38,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 99999,
            })

        # Success: just running (3 successes)
        for i in range(60, 63):
            logs.append({
                "storyboard_id": storyboard_id,
                "scene_id": i,
                "prompt": "1girl, running, park",
                "tags_used": ["1girl", "running", "park"],
                "status": "success",
                "match_rate": 0.88,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 99998,
            })

        # Success: just sleeping (3 successes) -> This proves "sleeping" itself is not the issue
        for i in range(70, 73):
            logs.append({
                "storyboard_id": storyboard_id,
                "scene_id": i,
                "prompt": "1girl, sleeping, park",
                "tags_used": ["1girl", "sleeping", "park"],
                "status": "success",
                "match_rate": 0.85,
                "sd_params": {"steps": 20, "cfg_scale": 7},
                "seed": 99997,
            })

        print(f"Creating {len(logs)} test logs...")

        for log_data in logs:
            log = ActivityLog(**log_data)
            db.add(log)
        
        db.commit()
        print(f"✅ Created {len(logs)} logs")
        print()
        
        # 3. Get suggestions via API
        print("Getting conflict rule suggestions...")
        response = requests.get(
            f"{API_BASE}/activity-logs/suggest-conflict-rules",
            params={
                "storyboard_id": storyboard_id, # UDPATED: Using storyboard_id
                "min_occurrences": 3, # Lowered slightly for strict test set
                "fail_rate_threshold": 0.6
            }
        )

        if response.status_code == 200:
            result = response.json()
            print(f"Found {result.get('new_rules_count', 0)} new suggestions")

            # Find running + sleeping
            conflict_pair = None
            for rule in result.get("suggested_rules", []):
                if {rule["tag1"], rule["tag2"]} == {"running", "sleeping"}:
                    conflict_pair = rule
                    break

            if conflict_pair:
                print("\n✅ Found 'running + sleeping' conflict:")
                print(json.dumps(conflict_pair, indent=2))
                print()

                # Apply it
                print("Applying rule...")
                apply_response = requests.post(
                    f"{API_BASE}/activity-logs/apply-conflict-rules",
                    json={"rules": [{"tag1": "running", "tag2": "sleeping"}]}
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
                print(json.dumps(result.get("suggested_rules", []), indent=2))
        else:
            print(f"❌ Suggest failed: {response.status_code}")
            print(response.text)

    except Exception as exc:
        print(f"❌ Error: {exc}")
        db.rollback()
    finally:
        # Cleanup
        if storyboard_id:
            print("\nCleaning up test data...")
            try:
                # Delete logs first (orphan check handled via cascade usually, but explicit is safe)
                db.query(ActivityLog).filter(ActivityLog.storyboard_id == storyboard_id).delete()
                # Delete storyboard
                db.query(Storyboard).filter(Storyboard.id == storyboard_id).delete()
                db.commit()
                print("✅ Cleanup complete")
            except Exception as e:
                print(f"⚠️ Cleanup failed: {e}")
        
        db.close()

if __name__ == "__main__":
    main()
