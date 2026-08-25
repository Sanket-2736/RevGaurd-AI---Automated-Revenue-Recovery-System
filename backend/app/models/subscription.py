from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Subscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)
    plan_name: str
    amount: float
    currency: str = Field(default="USD")
    status: str = Field(index=True)
    next_billing_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
