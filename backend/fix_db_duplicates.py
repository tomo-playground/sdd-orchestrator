import sys
import os

# Add the current directory to sys.path to import local modules
sys.path.append(os.getcwd())

from database import SessionLocal
from sqlalchemy import text

def fix_duplicates():
    db = SessionLocal()
    try:
        print("Checking for duplicates in classification_rules...")
        # Get duplicates
        query = text("""
            SELECT rule_type, pattern, array_agg(id) as ids
            FROM classification_rules
            GROUP BY rule_type, pattern
            HAVING count(*) > 1;
        """)
        result = db.execute(query).fetchall()
        
        if not result:
            print("No duplicates found.")
            return

        for row in result:
            rule_type, pattern, ids = row
            # Keep the first ID, delete others
            to_delete = ids[1:]
            print(f"Deleting duplicates for ({rule_type}, {pattern}): IDs {to_delete}")
            db.execute(
                text("DELETE FROM classification_rules WHERE id = ANY(:ids)"),
                {"ids": to_delete}
            )
        
        db.commit()
        print("Duplicates cleared successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_duplicates()
