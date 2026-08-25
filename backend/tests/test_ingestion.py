from sqlmodel import SQLModel
from app.db import engine
from app.routers.ingestion import ingest_all_synthetic_data
import app.models  # register metadata

def test_ingest_all():
    # Create tables in SQLite
    SQLModel.metadata.create_all(engine)

    result = ingest_all_synthetic_data()
    print("Ingestion Result:", result)

    assert result["customers"] == 200
    assert result["payments"] == 350
    assert result["checkouts"] == 250
    assert result["subscriptions"] == 200
    assert result["invoices"] == 200
    print("Ingestion test passed successfully!")

if __name__ == "__main__":
    test_ingest_all()
