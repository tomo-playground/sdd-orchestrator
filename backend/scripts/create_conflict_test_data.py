"""Create test generation logs with conflict patterns for rule discovery testing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models.activity_log import ActivityLog


def main():
    db = SessionLocal()
    try:
        # Conflict pattern 1: upper body + full body (should fail)
        conflict_logs_1 = [
            {
                "scene_index": i,
                "prompt": "1girl, sitting, upper body, full body, classroom",
                "tags": ["1girl", "sitting", "upper body", "full body", "classroom"],
                "status": "fail",
                "match_rate": 0.45,
            }
            for i in range(10, 20)  # 10 fails
        ]

        # Conflict pattern 2: indoors + outdoors (should fail)
        conflict_logs_2 = [
            {
                "scene_index": i,
                "prompt": "1girl, standing, indoors, outdoors, city",
                "tags": ["1girl", "standing", "indoors", "outdoors", "city"],
                "status": "fail",
                "match_rate": 0.40,
            }
            for i in range(20, 28)  # 8 fails
        ]

        # Conflict pattern 3: day + night (should fail)
        conflict_logs_3 = [
            {
                "scene_index": i,
                "prompt": "landscape, day, night, dramatic",
                "tags": ["landscape", "day", "night", "dramatic"],
                "status": "fail",
                "match_rate": 0.35,
            }
            for i in range(30, 37)  # 7 fails
        ]

        # Success cases (no conflicts)
        success_logs = [
            {
                "scene_index": i,
                "prompt": "1girl, sitting, upper body, classroom",
                "tags": ["1girl", "sitting", "upper body", "classroom"],
                "status": "success",
                "match_rate": 0.85,
            }
            for i in range(40, 43)  # 3 successes
        ]

        all_logs = conflict_logs_1 + conflict_logs_2 + conflict_logs_3 + success_logs

        print(f"Creating {len(all_logs)} test generation logs...")
        print("  - 10 logs with 'upper body + full body' conflict (fail)")
        print("  - 8 logs with 'indoors + outdoors' conflict (fail)")
        print("  - 7 logs with 'day + night' conflict (fail)")
        print("  - 3 logs without conflicts (success)")
        print()

        for log_data in all_logs:
            log = ActivityLog(
                scene_id=log_data["scene_index"],
                prompt=log_data["prompt"],
                tags_used=log_data["tags"],
                sd_params={"steps": 20, "cfg_scale": 7},
                match_rate=log_data["match_rate"],
                status=log_data["status"],
                seed=12345,
            )
            db.add(log)

        db.commit()
        print(f"✅ Created {len(all_logs)} test logs")
        print()
        print("Next steps:")
        print("  1. curl 'http://localhost:8000/generation-logs/suggest-conflict-rules?min_occurrences=5'")
        print("  2. Review suggested rules")
        print("  3. Apply rules via POST /generation-logs/apply-conflict-rules")

    except Exception as exc:
        db.rollback()
        print(f"❌ Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
