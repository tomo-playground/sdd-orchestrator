import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv('backend/.env')
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    result = conn.execute(text("SELECT id, scene_id, image_url, status FROM activity_logs ORDER BY id DESC LIMIT 5"))
    for row in result:
        print(row)
