import os
import sys

# MANDATORY: Override DATABASE_URL to in-memory SQLite before any app modules are imported
os.environ["DATABASE_URL"] = "sqlite://"

# Ensure backend root directory is on sys.path for direct pytest invocation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

import app.db

# Create isolated in-memory SQLite engine for unit tests
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Patch app.db.engine to test_engine
app.db.engine = test_engine

@pytest.fixture(name="engine")
def engine_fixture():
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    yield test_engine

@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(test_engine) as session:
        yield session
