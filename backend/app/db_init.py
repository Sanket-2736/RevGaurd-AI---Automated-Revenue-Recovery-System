from sqlmodel import SQLModel
from app.db import engine
# Import all models to ensure SQLModel registers them in metadata
import app.models  # noqa: F401

def create_db_and_tables():
    print("Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    create_db_and_tables()
