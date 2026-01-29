import requests
import time
from sqlalchemy.orm import Session
from database import SessionLocal
from models.lora import LoRA

CIVITAI_API_URL = "https://civitai.com/api/v1/models"

def search_civitai_model(query: str):
    """Search for a model on Civitai by name."""
    try:
        # Search by query
        resp = requests.get(CIVITAI_API_URL, params={"query": query, "limit": 1})
        resp.raise_for_status()
        data = resp.json()
        
        items = data.get("items", [])
        if not items:
            return None
            
        model = items[0]
        # Get the latest version or specific version? 
        # Usually users want the version that matches their file, but name matching is fuzzy.
        # Let's use the first model's latest version triggers for now.
        if not model.get("modelVersions"):
            return None
            
        # Prefer version that matches query if possible, else take first
        # But here query is filename-ish.
        version = model["modelVersions"][0]
        return {
            "id": model["id"],
            "name": model["name"],
            "version_id": version["id"],
            "version_name": version["name"],
            "triggers": version.get("trainedWords", [])
        }
        
    except Exception as e:
        print(f"❌ Error searching Civitai for '{query}': {e}")
        return None

import argparse

def sync_triggers(dry_run: bool = False):
    db = SessionLocal()
    try:
        loras = db.query(LoRA).all()
        print(f"🔄 Found {len(loras)} LoRAs in DB. Starting sync (Dry Run: {dry_run})...")
        
        updated_count = 0
        
        for lora in loras:
            # Clean name for search
            search_query = lora.name.replace("_", " ")
            
            print(f"🔍 Searching for '{lora.name}' (query: '{search_query}')...")
            
            # Simple rate limiting
            time.sleep(0.5)
            
            result = search_civitai_model(search_query)
            if result:
                triggers = result["triggers"]
                print(f"   ✅ Found: {result['name']} ({result['version_name']})")
                print(f"   🔑 Triggers: {triggers}")
                
                if triggers:
                    # Check for changes
                    if set(lora.trigger_words or []) != set(triggers):
                        if not dry_run:
                            lora.trigger_words = triggers
                            lora.civitai_id = result["id"]
                            updated_count += 1
                            print("   💾 Updated DB.")
                        else:
                            print("   👀 [Dry Run] Would update DB.")
                    else:
                        print("   Unknown changes (already up to date).")
            else:
                print("   ❌ Not found on Civitai.")
        
        if not dry_run:
            db.commit()
            print(f"✨ Sync complete. Updated {updated_count} LoRAs.")
        else:
            print("✨ Dry run complete. No changes made.")
        
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync LoRA trigger words from Civitai")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving")
    args = parser.parse_args()
    
    sync_triggers(dry_run=args.dry_run)
