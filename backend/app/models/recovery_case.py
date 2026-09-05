from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from app.models.enums import CaseType, CaseStatus, DecisionSource

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class RecoveryCase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_type: CaseType = Field(index=True)
    source_id: Optional[int] = Field(default=None, index=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)

    amount_at_risk: float
    status: CaseStatus = Field(default=CaseStatus.DETECTED, index=True)
    root_cause: Optional[str] = None
    recommended_action: Optional[str] = None
    ai_confidence: Optional[float] = None
    decision_source: Optional[DecisionSource] = Field(default=DecisionSource.AI_PRIMARY, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = None
