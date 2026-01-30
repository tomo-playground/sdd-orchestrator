
from sqlalchemy import text

from database import engine


def migrate():
    with engine.connect() as conn:
        print("Migrating loras table...")
        conn.execute(text('ALTER TABLE loras ADD COLUMN IF NOT EXISTS optimal_weight NUMERIC(3, 2)'))
        conn.execute(text('ALTER TABLE loras ADD COLUMN IF NOT EXISTS calibration_score INTEGER'))
        conn.execute(text('ALTER TABLE loras ADD COLUMN IF NOT EXISTS weight_min NUMERIC(3, 2) DEFAULT 0.1'))
        conn.execute(text('ALTER TABLE loras ADD COLUMN IF NOT EXISTS weight_max NUMERIC(3, 2) DEFAULT 1.0'))
        conn.commit()
        print("Success!")

if __name__ == "__main__":
    migrate()
