from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
# Connect to 'postgres' database to list others
base_url = os.getenv("DATABASE_URL").rsplit('/', 1)[0] + '/postgres'
engine = create_engine(base_url)

def list_dbs():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT datname FROM pg_database WHERE datistemplate = false;"))
        dbs = [r[0] for r in res]
        print(f"Databases: {dbs}")

if __name__ == "__main__":
    list_dbs()
