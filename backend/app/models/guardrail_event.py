from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from app.models.enums import GuardrailDecision

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class GuardrailEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="recoverycase.id", index=True)
    rule_triggered: str
    decision: GuardrailDecision = Field(index=True)
    reason: str
    created_at: datetime = Field(default_factory=utc_now)
