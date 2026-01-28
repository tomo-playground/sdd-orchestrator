from database import engine
from sqlalchemy import text, inspect

def check_db():
    print(f"Connecting to: {engine.url}")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables found: {tables}")
    
    with engine.connect() as conn:
        for table in tables:
            try:
                count = conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
                print(f"Table {table}: {count} records")
            except Exception as e:
                print(f"Could not count {table}: {e}")
        
        try:
            res = conn.execute(text('SELECT version_num FROM alembic_version')).fetchone()
            print(f"Alembic Version: {res[0] if res else 'None'}")
        except Exception as e:
            print(f"Could not get alembic version: {e}")

if __name__ == "__main__":
    check_db()
