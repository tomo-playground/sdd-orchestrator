import os
import sys

# Add backend directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.tag import Tag


def verify_import():
    session = SessionLocal()
    try:
        print("🔍 Verifying Tag Import Layering...")

        # Check specific key tags
        test_cases = [
            ("masterpiece", 0, "ANY"),
            ("1girl", 1, "ANY"),
            ("blue_eyes", 2, "PERMANENT"),
            ("long_hair", 2, "PERMANENT"),
            ("large_breasts", 3, "PERMANENT"),
            ("school_uniform", 4, "ANY"),
            ("red_ribbon", 6, "ANY"),
            ("smile", 7, "TRANSIENT"),
            ("sitting", 8, "TRANSIENT"),
            ("looking_at_viewer", 8, "TRANSIENT"),
            ("close-up", 9, "TRANSIENT"),
            ("classroom", 10, "TRANSIENT"),
            ("sunset", 11, "TRANSIENT"),
            ("anime", 11, "TRANSIENT"),
        ]

        failed = 0
        for name, expected_layer, expected_scope in test_cases:
            tag = session.query(Tag).filter(Tag.name == name).first()
            if not tag:
                print(f"❌ '{name}' not found!")
                failed += 1
                continue

            if tag.default_layer != expected_layer or tag.usage_scope != expected_scope:
                print(
                    f"❌ '{name}': Expected L{expected_layer}/{expected_scope}, Got L{tag.default_layer}/{tag.usage_scope}"
                )
                failed += 1
            else:
                print(f"✅ '{name}': L{tag.default_layer} / {tag.usage_scope}")

        total_count = session.query(Tag).count()
        print(f"\n📊 Total Tags: {total_count}")

        if failed == 0:
            print("🎉 ALL CHECKS PASSED!")
        else:
            print(f"⚠️ {failed} CHECKS FAILED.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    verify_import()
