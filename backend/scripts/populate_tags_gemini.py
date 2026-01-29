
import sys
import os
import json
import time

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.tag import Tag
from config import gemini_client, GEMINI_TEXT_MODEL, logger

BATCH_SIZE = 5

def populate_tags():
    if not gemini_client:
        print("❌ GEMINI_API_KEY is not set.")
        return

    session = SessionLocal()
    try:
        # Fetch tags missing ko_name or description
        print("🔍 Fetching incomplete tags...")
        tags_to_update = session.query(Tag).filter(
            (Tag.ko_name == None) | (Tag.ko_name == "") | 
            (Tag.description == None) | (Tag.description == "")
        ).all()

        total = len(tags_to_update)
        print(f"📋 Found {total} tags to update.")

        if total == 0:
            print("✨ All tags are already populated!")
            return

        # Process in batches
        for i in range(0, total, BATCH_SIZE):
            batch = tags_to_update[i : i + BATCH_SIZE]
            tag_names = [t.name for t in batch]
            
            print(f"🔄 Processing batch {i//BATCH_SIZE + 1}/{(total + BATCH_SIZE - 1)//BATCH_SIZE}: {tag_names}")

            prompt = (
                "You are an expert anime tag translator. "
                "For the following list of Danbooru tags, provide the Korean translation ('ko_name') "
                "and a brief English description ('description').\n"
                "Return valid JSON object where keys are tag names.\n"
                "Example format:\n"
                "{\n"
                '  "looking_at_viewer": {"ko_name": "시선 맞춤", "description": "Character looking directly at the viewer"},\n'
                '  "simple_background": {"ko_name": "단순 배경", "description": "Background with minimal details"}\n'
                "}\n\n"
                f"Tags to translate: {json.dumps(tag_names)}"
            )

            retries = 5
            while retries > 0:
                try:
                    response = gemini_client.models.generate_content(
                        model=GEMINI_TEXT_MODEL,
                        contents=prompt
                    )
                    
                    # Clean up response
                    text = response.text.replace("```json", "").replace("```", "").strip()
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        print(f"   ⚠️ JSON Parse Error, skipping batch.")
                        break

                    # Update tags
                    updated_count = 0
                    for tag in batch:
                        if tag.name in data:
                            info = data[tag.name]
                            if not tag.ko_name:
                                tag.ko_name = info.get("ko_name")
                            if not tag.description:
                                tag.description = info.get("description")
                            updated_count += 1
                    
                    session.commit()
                    print(f"   ✅ Updated {updated_count} tags in this batch.")
                    break # Success, exit retry loop
                    
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                        print(f"   ⏳ Rate limit hit (429), retrying in {6-retries}0s...")
                        time.sleep((6-retries) * 10) # 10s, 20s, 30s...
                        retries -= 1
                    else:
                        print(f"   ❌ Batch failed: {e}")
                        break
            
            # Rate limiting niceness
            time.sleep(2)

        print("\n✨ Population Complete!")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    populate_tags()
