import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

def drop_all_tables():
    """Drops all tables in the public schema."""
    print("🔥 DROPPING ALL TABLES in public schema...")
    
    query = text("""
        DROP SCHEMA public CASCADE;
        CREATE SCHEMA public;
        GRANT ALL ON SCHEMA public TO postgres;
        GRANT ALL ON SCHEMA public TO public;
    """)
    
    with engine.connect() as conn:
        conn.execute(query)
        conn.commit()
    
    print("✨ Database is now completely empty.")

if __name__ == "__main__":
    drop_all_tables()
