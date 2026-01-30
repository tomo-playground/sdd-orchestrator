import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.storyboard import Storyboard
from models.activity_log import ActivityLog
from models.scene_quality import SceneQualityScore
from sqlalchemy import delete

def cleanup_orphans():
    db = SessionLocal()
    try:
        # ActivityLog Cleanup
        log_query = db.query(ActivityLog).filter(ActivityLog.storyboard_id == None)
        orphaned_logs_count = log_query.count()
        print(f"Found {orphaned_logs_count} orphaned ActivityLogs (storyboard_id is None)")
        
        if orphaned_logs_count > 0:
            db.query(ActivityLog).filter(ActivityLog.storyboard_id == None).delete(synchronize_session=False)
            print(f"Deleted {orphaned_logs_count} ActivityLogs")

        # SceneQualityScore Cleanup
        score_query = db.query(SceneQualityScore).filter(SceneQualityScore.storyboard_id == None)
        orphaned_scores_count = score_query.count()
        print(f"Found {orphaned_scores_count} orphaned SceneQualityScores (storyboard_id is None)")
        
        if orphaned_scores_count > 0:
            db.query(SceneQualityScore).filter(SceneQualityScore.storyboard_id == None).delete(synchronize_session=False)
            print(f"Deleted {orphaned_scores_count} SceneQualityScores")

        db.commit()
        print("Cleanup complete.")

    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_orphans()
