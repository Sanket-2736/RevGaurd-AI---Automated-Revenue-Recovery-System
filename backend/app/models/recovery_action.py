from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class RecoveryAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="recoverycase.id", index=True)
    action_type: str = Field(index=True)
    channel: Optional[str] = None
    payload: Optional[str] = None
    status: str = Field(default="PENDING", index=True)
    executed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
