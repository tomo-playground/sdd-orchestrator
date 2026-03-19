import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL)


def migrate():
    with engine.connect() as conn:
        print("Adding columns to scenes table...")
        conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS voice_design_prompt TEXT"))
        conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS head_padding FLOAT DEFAULT 0.0"))
        conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS tail_padding FLOAT DEFAULT 0.0"))
        conn.commit()
        print("Migration complete.")


if __name__ == "__main__":
    migrate()
