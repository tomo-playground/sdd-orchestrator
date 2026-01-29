from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
engine = create_engine(os.getenv('DATABASE_URL'))
inspector = inspect(engine)
columns = inspector.get_columns('activity_logs')
print(f"--- activity_logs columns ---")
for col in columns:
    print(f"{col['name']}: {col['type']}")
