"""Force fix all absolute URLs in DB to relative paths."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from database import SessionLocal
from models import Character, ActivityLog
from config import logger

def fix_url(url):
    if not url:
        return url
    if url.startswith("http"):
        # Extract path after the host
        # Example: http://127.0.0.1:8000/outputs/images/stored/scene_...ping
        try:
            from urllib.parse import urlparse
            path = urlparse(url).path
            return path
        except:
            return url
    return url

def main():
    db = SessionLocal()
    try:
        # Fix Characters
        chars = db.query(Character).all()
        char_count = 0
        for char in chars:
            new_url = fix_url(char.preview_image_url)
            if new_url != char.preview_image_url:
                logger.info(f"Fixed Character {char.name}: {char.preview_image_url} -> {new_url}")
                char.preview_image_url = new_url
                char_count += 1
        
        # Avoid fixing ActivityLog if it's too much, but let's try for recent ones
        logs = db.query(ActivityLog).filter(ActivityLog.image_url.like("http%")).all()
        log_count = 0
        for log in logs:
            new_url = fix_url(log.image_url)
            if new_url != log.image_url:
                log.image_url = new_url
                log_count += 1
        
        db.commit()
        logger.info(f"🎉 Cleanup complete! Fixed {char_count} characters and {log_count} activity logs.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error during cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
