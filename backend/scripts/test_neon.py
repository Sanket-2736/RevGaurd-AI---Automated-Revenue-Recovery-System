import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from app.db import engine
from sqlmodel import Session, text

def test_neon():
    print("Testing connection to Neon Postgres...")
    print("DATABASE_URL:", os.getenv("DATABASE_URL"))
    with Session(engine) as session:
        version = session.exec(text("SELECT version();")).first()
        print("Connected to Neon Postgres Successfully!")
        print("PostgreSQL Version:", version[0])

if __name__ == "__main__":
    test_neon()
