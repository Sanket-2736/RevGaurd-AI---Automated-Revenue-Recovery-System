from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)
    amount: float
    currency: str = Field(default="USD")
    status: str = Field(index=True)
    failure_reason: Optional[str] = None
    payment_method: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
