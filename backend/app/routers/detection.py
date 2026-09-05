import logging
from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db import get_session
from app.services.detection import detect_revenue_at_risk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/detection", tags=["detection"])

@router.post("/run")
def run_detection(session: Session = Depends(get_session)):
    """
    Scans payments, checkouts, subscriptions, and invoices for at-risk records
    and idempotently creates RecoveryCase records with status=DETECTED.
    Returns: {"cases_created": N, "total_at_risk": X}
    """
    logger.info("[API] POST /api/detection/run")
    result = detect_revenue_at_risk(session)
    logger.info(f"[API RESPONSE] POST /api/detection/run status=200 result={result}")
    return result
