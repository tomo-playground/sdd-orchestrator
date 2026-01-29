from database import SessionLocal
from models.tag import Tag

def check_tag():
    db = SessionLocal()
    tag = db.query(Tag).filter(Tag.name == "best_quality").first()
    if tag:
        print(f"Tag: {tag.name}, Category: {tag.category}")
    else:
        print("Tag not found")
    db.close()

if __name__ == "__main__":
    check_tag()
