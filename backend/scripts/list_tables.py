
from sqlalchemy import inspect

from database import engine


def list_tables():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("Existing tables:")
    for table in tables:
        print(f"- {table}")

if __name__ == "__main__":
    list_tables()
