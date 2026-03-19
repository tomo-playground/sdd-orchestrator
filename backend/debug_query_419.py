import json
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

query = text("""
    SELECT s.id, s.storyboard_id, s."order", s.image_asset_id, m.storage_key, s.candidates, s.image_prompt
    FROM scenes s
    LEFT JOIN media_assets m ON s.image_asset_id = m.id
    WHERE s.storyboard_id = 419
    ORDER BY s."order";
""")

with engine.connect() as conn:
    result = conn.execute(query)
    for row in result:
        print(f"Scene Order: {row.order}")
        print(f"  ID: {row.id}")
        print(f"  ImageAssetID: {row.image_asset_id}")
        print(f"  StorageKey: {row.storage_key}")
        print(f"  ImagePrompt: {row.image_prompt[:50]}...")
        print(f"  Candidates: {json.dumps(row.candidates)[:100]}...")
        print("-" * 20)
