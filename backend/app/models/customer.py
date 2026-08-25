from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True, unique=True)
    name: str
    email: str = Field(index=True)
    phone: Optional[str] = None
    risk_score: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=utc_now)
