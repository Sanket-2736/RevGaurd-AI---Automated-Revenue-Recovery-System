from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db import get_session
from app.services.detection import detect_revenue_at_risk

router = APIRouter(prefix="/api/detection", tags=["detection"])

@router.post("/run")
def run_detection(session: Session = Depends(get_session)):
    """
    Scans payments, checkouts, subscriptions, and invoices for at-risk records
    and idempotently creates RecoveryCase records with status=DETECTED.
    Returns: {"cases_created": N, "total_at_risk": X}
    """
    return detect_revenue_at_risk(session)
