
from database import engine
from sqlalchemy import inspect

def list_tables():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("Existing tables:")
    for table in tables:
        print(f"- {table}")

if __name__ == "__main__":
    list_tables()
